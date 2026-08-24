#!/usr/bin/env python3
"""CT パイロットのタスク単位比較（機構の可視化）.

レーン継続の利得（再探索の回避＝ターン数減）と代償（文脈の肥大＝1ターンの高コスト化）が
同じタスクの上でどう相殺するかを見る。C′ の閾値 H* の位置を経験的に絞る材料にもする。
"""
from __future__ import annotations

import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "runs/ctpilot")
rows: dict[str, dict] = {}
for p in root.rglob("calls.jsonl"):
    for line in p.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        tid = r.get("task_id") or "CT-A(id欠落)"
        rows.setdefault(tid, {})[r["arm"]] = r

hdr = f"{'task':<16}{'arm':<5}{'turns':>6}{'cache_r':>11}{'cache_w':>9}{'peak_H':>9}{'cost':>9}"
print(hdr)
print("-" * len(hdr))
tot = {"B": 0.0, "C": 0.0}
for tid in sorted(rows):
    for arm in ("B", "C"):
        r = rows[tid].get(arm)
        if not r:
            continue
        tot[arm] += r["cost_usd"]
        print(f"{tid:<16}{arm:<5}{r.get('num_turns') or 0:>6}"
              f"{r['cache_read_tokens']:>11,}{r['cache_creation_tokens']:>9,}"
              f"{r.get('peak_context_tokens') or 0:>9,}{r['cost_usd']:>9.3f}")
    b, c = rows[tid].get("B"), rows[tid].get("C")
    if b and c:
        d = (c["cost_usd"] - b["cost_usd"]) / b["cost_usd"] if b["cost_usd"] else 0
        dt = (c.get("num_turns") or 0) - (b.get("num_turns") or 0)
        print(f"{'':<16}{'→':<5}{'':>6}{'':>11}{'':>9}{'':>9}{d:>+8.1%}"
              f"   turns差={dt:+d}  resumed={c.get('resumed')}")
    print()

print(f"合計  B=${tot['B']:.3f}  C=${tot['C']:.3f}  "
      f"差={(tot['C'] - tot['B']) / tot['B']:+.1%}")

# --- C′ の閾値判断に効く量 ---
print("\n=== C′（予算付きレーン）の判断材料 ===")
resumed = [(t, r["C"]) for t, r in rows.items()
           if "C" in r and r["C"].get("resumed")]
if resumed:
    print("resume したタスクの H と、その回の損得:")
    for tid, c in sorted(resumed):
        b = rows[tid].get("B")
        if not b:
            continue
        d = (c["cost_usd"] - b["cost_usd"]) / b["cost_usd"]
        h = c.get("peak_context_tokens") or 0
        verdict = "得" if d < 0 else "損"
        print(f"  {tid:<10} H={h:>8,}  {d:+.1%}  → {verdict}")
    print("\n  H* は「得→損」が反転する H の位置にある。")
    print("  全て損なら H* はこのレーンの最小 H より下＝C′ は早期に分割すべき。")
    print("  全て得なら H* はレーンの最大 H より上＝C′ は分割せず C と同一動作。")
