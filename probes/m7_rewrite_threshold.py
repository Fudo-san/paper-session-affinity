#!/usr/bin/env python3
"""M7: 初回 resume で履歴が書き直される（ρ=1）閾値を特定する.

背景【A6】(M6, 2026-08-04): resume 直後の1回だけ、追加プロンプトが大きいと
継承履歴 H 相当が書き直される。300文字では発生せず、20,000文字で発生した。
warm/cold（TTL）とは独立のトリガであり、閾値そのものは未特定（2点しかない）。

問い: **ρ=1 に切り替わる追加プロンプトサイズはどこか。**
これは C′ の制御変数になる（初回プロンプトを閾値未満に抑えれば ρ=0 を維持でき、
§3.5 の H* が約2倍になる）。

方法: 追加量を対数スイープし、各点で「1測定=1新規セッション+一意プレフィックス」。
    init（プレフィックスのみ）→ 即 resume（payload X 文字）→ 分類
分類（測定前に固定。M6 と同一基準）:
    ρ=0 … cache_read ≥ 0.9·H0   （履歴をキャッシュから読んだ）
    ρ=1 … それ以外               （履歴が読まれていない＝書き直し）

結果は m7_results.jsonl へ **追記のみ**。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "m7_results.jsonl"
PREFIX_LINES = 500
READ_RATIO = 0.9          # 測定前に固定
DEFAULT_POINTS = [500, 1000, 2000, 4000, 8000, 16000]


def find_claude() -> str | None:
    exe = shutil.which("claude")
    if exe:
        return exe
    for c in [Path.home() / ".local" / "bin" / "claude",
              Path.home() / ".npm-global" / "bin" / "claude"]:
        if c.exists():
            return str(c)
    return None


def cli_version(exe: str) -> str:
    try:
        p = subprocess.run([exe, "--version"], capture_output=True, timeout=30)
        return p.stdout.decode(errors="replace").strip()[:120]
    except Exception as exc:
        return f"unknown ({exc})"


def build_prefix(nonce: str) -> str:
    return (f"## Project context (m7 nonce={nonce})\n"
            + "\n".join(
                f"- probe rule {i:04d}: keep interfaces stable, write focused tests, "
                "never edit files outside declared scope." for i in range(PREFIX_LINES)
            ))


def build_payload(nonce: str, chars: int) -> str:
    unit = (f"[{nonce}] record {{i:05d}}: value=stable, owner=probe, "
            "note=synthetic tool output line.\n")
    n = max(1, chars // len(unit.format(i=0)))
    return "".join(unit.format(i=i) for i in range(n))


def call(exe: str, prompt: str, label: str, meta: dict,
         resume: str | None = None) -> dict:
    cmd = [exe, "--print", "--output-format", "json"]
    if resume:
        cmd += ["--resume", resume]
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt.encode("utf-8"),
                          capture_output=True, timeout=900)
    rec: dict = {"label": label, "resume": bool(resume), "rc": proc.returncode,
                 "wall_s": round(time.time() - t0, 1),
                 "iso": datetime.now(timezone.utc).astimezone().isoformat(), **meta}
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        u = data.get("usage") or {}
        cw = u.get("cache_creation_input_tokens") or 0
        cr = u.get("cache_read_input_tokens") or 0
        rec.update({"session_id": data.get("session_id"),
                    "input": u.get("input_tokens"), "output": u.get("output_tokens"),
                    "cache_w": cw, "cache_r": cr, "ctx_total": cw + cr,
                    "cost_usd": data.get("total_cost_usd"), "raw": data})
    except Exception as exc:
        rec["parse_error"] = str(exc)
        rec["stderr"] = proc.stderr.decode(errors="replace")[:800]
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def measure_point(exe: str, chars: int, rep: int, cli_ver: str) -> dict | None:
    nonce = uuid.uuid4().hex[:12]
    base = {"probe": "m7", "payload_chars": chars, "rep": rep,
            "nonce": nonce, "cli_version": cli_ver, "prefix_lines": PREFIX_LINES}
    r0 = call(exe, build_prefix(nonce) + "\n## Q\nReply with exactly: OK",
              f"m7_c{chars}_r{rep}_init", {**base, "phase": "init"})
    sid = r0.get("session_id")
    if not sid or r0["rc"] != 0:
        print(f"  [SKIP] chars={chars} rep={rep}: init failed", file=sys.stderr, flush=True)
        return None
    h0 = r0.get("ctx_total") or 0

    payload = build_payload(nonce, chars)
    r1 = call(exe, f"{payload}\n## Q\nReply with exactly: OK-2",
              f"m7_c{chars}_r{rep}_resume", {**base, "phase": "resume", "H0": h0},
              resume=sid)
    cr, cw = r1.get("cache_r") or 0, r1.get("cache_w") or 0
    read_ratio = (cr / h0) if h0 else 0.0
    rho = 0 if read_ratio >= READ_RATIO else 1

    s = {"label": f"m7_c{chars}_r{rep}_verdict", **base,
         "iso": datetime.now(timezone.utc).astimezone().isoformat(),
         "H0": h0, "cache_r": cr, "cache_w": cw,
         "read_ratio": round(read_ratio, 4), "rho": rho,
         "payload_tokens_est": (r1.get("ctx_total") or 0) - h0,
         "cost_init_usd": r0.get("cost_usd"), "cost_resume_usd": r1.get("cost_usd")}
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"  chars={chars:>6,}  H0={h0:>7,}  cache_r={cr:>7,}  cache_w={cw:>7,}  "
          f"read/H0={read_ratio:.3f}  rho={rho}", flush=True)
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--points", type=int, nargs="*", default=DEFAULT_POINTS)
    ap.add_argument("--reps", type=int, default=1)
    args = ap.parse_args()

    exe = find_claude()
    if not exe:
        print("[ERROR] claude CLI not found", file=sys.stderr)
        return 1
    ver = cli_version(exe)
    print(f"M7 rewrite-threshold  cli={ver}  points={args.points}", flush=True)
    print(f"  分類: read/H0 >= {READ_RATIO} を rho=0（履歴を読んだ）とする\n", flush=True)

    results = []
    for chars in args.points:
        for rep in range(1, args.reps + 1):
            s = measure_point(exe, chars, rep, ver)
            if s:
                results.append(s)

    print("\n=== まとめ ===", flush=True)
    print(f"{'chars':>8} {'payload_tok':>12} {'read/H0':>9} {'rho':>4}", flush=True)
    for s in results:
        print(f"{s['payload_chars']:>8,} {s['payload_tokens_est']:>12,} "
              f"{s['read_ratio']:>9.3f} {s['rho']:>4}", flush=True)

    zeros = [s["payload_chars"] for s in results if s["rho"] == 0]
    ones = [s["payload_chars"] for s in results if s["rho"] == 1]
    verdict = {"rho0_max_chars": max(zeros) if zeros else None,
               "rho1_min_chars": min(ones) if ones else None}
    if zeros and ones:
        print(f"\n閾値は {max(zeros):,} 〜 {min(ones):,} 文字の間", flush=True)
    elif zeros:
        print(f"\n全点で rho=0（{max(zeros):,} 文字までは書き直し発生せず）", flush=True)
    elif ones:
        print(f"\n全点で rho=1（{min(ones):,} 文字で既に発生）", flush=True)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"label": "m7_summary", "probe": "m7", "cli_version": ver,
                            "iso": datetime.now(timezone.utc).astimezone().isoformat(),
                            **verdict,
                            "points": [{k: s[k] for k in
                                        ("payload_chars", "payload_tokens_est",
                                         "read_ratio", "rho")} for s in results]},
                           ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
