#!/usr/bin/env python3
"""M6: 累積履歴 H に対する1ターンあたり cache_write の関係を測る.

背景（`fail-20260803-01`）: パイロットで resume 側の cache_write が増えた。
§3 は warm 境界で履歴が α_r（read）で運ばれるとだけ置いており、write が増える項を持たない。
その機構は未検証（ブレークポイント再配置か否か。CLI 実装は非公開）。

問い: **cache_write は累積履歴 H とともに増えるのか、それとも新規追加分だけで一定か。**

- 増える → 「運んだ履歴が以降の書き込みを膨らませる」を支持。§3 に H 依存の write 項が要る
- 一定   → 機構は別。パイロットの write 増は履歴長ではなく別要因（生成量など）に由来

方法: 1新規セッション（一意 nonce）→ 同一セッションを N 回 resume。
各 resume で一意ペイロード（既定 20k 文字）を足し、H を単調に増やしながら
毎回の cache_write / cache_read を記録する。応答は1語に固定し出力側の揺れを抑える。

結果は m6_results.jsonl へ **追記のみ**。
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

OUT = Path(__file__).resolve().parent / "m6_results.jsonl"
PREFIX_LINES = 500      # 初期履歴（約45k tokens 相当。既存プローブと揃える）
PAYLOAD_CHARS = 20_000  # 1 resume あたりの追加量（ツール結果の代わり）


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
    return (f"## Project context (m6 nonce={nonce})\n"
            + "\n".join(
                f"- probe rule {i:04d}: keep interfaces stable, write focused tests, "
                "never edit files outside declared scope." for i in range(PREFIX_LINES)
            ))


def build_payload(nonce: str, turn: int, chars: int) -> str:
    """毎回一意な追加ペイロード。既存キャッシュに当たらないよう turn と nonce を混ぜる。"""
    unit = (f"[{nonce}-t{turn:02d}] record {{i:05d}}: "
            "value=stable, owner=probe, note=synthetic tool output line.\n")
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
    rec: dict = {"label": label, "resume": bool(resume),
                 "rc": proc.returncode, "wall_s": round(time.time() - t0, 1),
                 "iso": datetime.now(timezone.utc).astimezone().isoformat(), **meta}
    try:
        data = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        u = data.get("usage") or {}
        cw = u.get("cache_creation_input_tokens") or 0
        cr = u.get("cache_read_input_tokens") or 0
        rec.update({
            "session_id": data.get("session_id"),
            "input": u.get("input_tokens"), "output": u.get("output_tokens"),
            "cache_w": cw, "cache_r": cr,
            "ctx_total": cw + cr,            # このリクエストのプロンプト全体（≒H）
            "cost_usd": data.get("total_cost_usd"),
            "raw": data,
        })
    except Exception as exc:
        rec["parse_error"] = str(exc)
        rec["stderr"] = proc.stderr.decode(errors="replace")[:800]
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"  turn={rec.get('turn','-'):>3} rc={rec['rc']} "
          f"ctx={rec.get('ctx_total',0):>7,} cache_w={rec.get('cache_w',0):>7,} "
          f"cache_r={rec.get('cache_r',0):>7,} out={rec.get('output',0):>5} "
          f"cost=${rec.get('cost_usd')}", flush=True)
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=8, help="resume 回数")
    ap.add_argument("--payload-chars", type=int, default=PAYLOAD_CHARS)
    ap.add_argument("--rep", type=int, default=1)
    args = ap.parse_args()

    exe = find_claude()
    if not exe:
        print("[ERROR] claude CLI not found", file=sys.stderr)
        return 1
    ver = cli_version(exe)
    nonce = uuid.uuid4().hex[:12]
    base = {"probe": "m6", "rep": args.rep, "nonce": nonce, "cli_version": ver,
            "payload_chars": args.payload_chars, "prefix_lines": PREFIX_LINES}

    print(f"M6 write-growth  claude={exe}  cli={ver}  nonce={nonce}", flush=True)
    r0 = call(exe, build_prefix(nonce) + "\n## Q\nReply with exactly: OK",
              "m6_init", {**base, "turn": 0})
    sid = r0.get("session_id")
    if not sid or r0["rc"] != 0:
        print("[ABORT] init failed", file=sys.stderr)
        return 1

    rows = [r0]
    for t in range(1, args.turns + 1):
        payload = build_payload(nonce, t, args.payload_chars)
        prompt = (f"{payload}\n## Q\nReply with exactly: OK-{t}")
        r = call(exe, prompt, f"m6_resume_t{t:02d}", {**base, "turn": t}, resume=sid)
        rows.append(r)
        if r["rc"] != 0:
            print(f"[STOP] turn {t} failed", file=sys.stderr)
            break

    # --- 集計: H（直前ターンの ctx_total）に対する cache_write ---------------
    print("\n=== H vs cache_write ===", flush=True)
    print(f"{'turn':>4} {'H_before':>10} {'cache_w':>9} {'cache_r':>9} {'w/H':>7}", flush=True)
    summary = []
    for i in range(1, len(rows)):
        h_before = rows[i - 1].get("ctx_total") or 0
        cw = rows[i].get("cache_w") or 0
        cr = rows[i].get("cache_r") or 0
        ratio = (cw / h_before) if h_before else 0.0
        print(f"{i:>4} {h_before:>10,} {cw:>9,} {cr:>9,} {ratio:>7.3f}", flush=True)
        summary.append({"turn": i, "H_before": h_before, "cache_w": cw,
                        "cache_r": cr, "w_over_H": round(ratio, 4)})

    verdict = "unknown"
    if len(summary) >= 4:
        first = [s["cache_w"] for s in summary[:2]]
        last = [s["cache_w"] for s in summary[-2:]]
        a, b = sum(first) / len(first), sum(last) / len(last)
        growth = (b / a) if a else 0
        # 判定基準は測定前に固定する（PROBE_PLAN §2 の作法）
        verdict = "grows_with_H" if growth >= 1.5 else ("flat" if growth <= 1.2 else "ambiguous")
        print(f"\n前半平均 cache_w={a:,.0f} / 後半平均={b:,.0f} / 比={growth:.2f}", flush=True)
        print(f"判定: {verdict}  "
              "[grows_with_H=履歴が書き込みを膨らませる / flat=新規分のみで一定]", flush=True)

    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"label": "m6_summary", **base,
                            "iso": datetime.now(timezone.utc).astimezone().isoformat(),
                            "verdict": verdict, "rows": summary}, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
