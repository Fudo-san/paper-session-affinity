#!/usr/bin/env python3
"""resume プローブ: 仮定【A3】の検証（Week 4 前倒し実施）.

検証内容: claude CLI の --resume で継承した履歴 H がキャッシュ可能プレフィックスとして
扱われるか。3ケースを測る:
  P1(warm):   直後に resume (g ≪ τ=5min)  → cache_read ≈ H を予測
  P2(cold):   6分超待って resume (g > τ)   → cache_creation ≈ H を予測
  P3(switch): モデル切替で resume          → キャッシュ全損（モデル別）を予測

結果は resume_probe_results.jsonl に1呼び出し1行で保存（rawごと）。
コスト: 20k トークン級 ×4 呼び出し（1ドル未満）。
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent / "resume_probe_results.jsonl"
PREFIX_LINES = 500  # 約30,000 chars。Opus系の最小キャッシュ4096トークンを確実に超える


def find_claude() -> str | None:
    exe = shutil.which("claude")
    if exe:
        return exe
    for c in [Path.home() / ".local" / "bin" / "claude",
              Path.home() / ".npm-global" / "bin" / "claude"]:
        if c.exists():
            return str(c)
    return None


def call(exe: str, prompt: str, label: str, resume: str | None = None,
         model: str | None = None) -> dict:
    cmd = [exe, "--print", "--output-format", "json"]
    if resume:
        cmd += ["--resume", resume]
    if model:
        cmd += ["--model", model]
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt.encode("utf-8"),
                          capture_output=True, timeout=600)
    rec: dict = {"label": label, "resume": bool(resume), "model_flag": model,
                 "rc": proc.returncode, "wall_s": round(time.time() - t0, 1),
                 "at": time.strftime("%H:%M:%S")}
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        u = data.get("usage") or {}
        rec.update({
            "session_id": data.get("session_id"),
            "input": u.get("input_tokens"),
            "output": u.get("output_tokens"),
            "cache_w": u.get("cache_creation_input_tokens"),
            "cache_r": u.get("cache_read_input_tokens"),
            "cost_usd": data.get("total_cost_usd"),
            "raw": data,
        })
    except Exception as exc:
        rec["parse_error"] = str(exc)
        rec["stderr"] = proc.stderr.decode(errors="replace")[:800]
        rec["stdout_head"] = proc.stdout.decode(errors="replace")[:400]
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[{rec['at']}] {label}: rc={rec['rc']} "
          f"in={rec.get('input')} cache_w={rec.get('cache_w')} "
          f"cache_r={rec.get('cache_r')} cost=${rec.get('cost_usd')}",
          flush=True)
    return rec


def main() -> int:
    exe = find_claude()
    if not exe:
        print("[ERROR] claude CLI not found", file=sys.stderr)
        return 1
    prefix = "## Project context (resume-probe)\n" + "\n".join(
        f"- probe rule {i:04d}: keep interfaces stable, write focused tests, "
        "never edit files outside declared scope." for i in range(PREFIX_LINES)
    )
    print(f"claude={exe} prefix_chars={len(prefix):,}", flush=True)

    r1 = call(exe, prefix + "\n## Q\nReply exactly: OK-1", "P0_initial")
    sid = r1.get("session_id")
    if not sid or r1["rc"] != 0:
        print("[ABORT] initial call failed or no session_id", file=sys.stderr)
        return 1

    r2 = call(exe, "Reply exactly: OK-2", "P1_warm_resume", resume=sid)

    print("[WAIT] 380s for TTL expiry...", flush=True)
    time.sleep(380)

    r3 = call(exe, "Reply exactly: OK-3", "P2_cold_resume", resume=sid)
    r4 = call(exe, "Reply exactly: OK-4", "P3_model_switch_resume",
              resume=sid, model="haiku")

    print("\n=== verdict hints ===", flush=True)
    if isinstance(r2.get("cache_r"), int) and isinstance(r1.get("cache_w"), int):
        ratio = r2["cache_r"] / max(1, (r1.get("cache_w") or 0) + (r1.get("cache_r") or 0))
        print(f"P1 warm: cache_r(P1)/total_ctx(P0) = {ratio:.2f} "
              "(≈1なら【A3】成立)", flush=True)
    if isinstance(r3.get("cache_w"), int):
        print(f"P2 cold: cache_w={r3['cache_w']} cache_r={r3.get('cache_r')} "
              "(履歴ぶんwrite優勢ならcold損益どおり)", flush=True)
    print("done. raw: resume_probe_results.jsonl", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
