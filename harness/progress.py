#!/usr/bin/env python3
"""S6 本実験の進捗を全反復ぶん集計する（run.json を正とする）。

台帳は追記専用で破棄した run の行も残るため、有効データはディスク側で数える。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABEL = sys.argv[1] if len(sys.argv) > 1 else "main"
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 14

RUNS = ROOT / "runs" / LABEL
specs = [s["spec_id"] for s in json.loads(
    (ROOT / "benchmarks" / "specs.json").read_text(encoding="utf-8"))["specs"]]

print(f"{'rep':<5}{'有効':>6}{'対':>5}{'片ア':>6}{'未着':>6}{'費用':>10}{'受入':>8}")
tot_cost = 0.0
tot_pairs = 0
done_reps = 0
for rep in range(1, REPS + 1):
    got = {}
    for spec in specs:
        for arm in ("B", "C"):
            rj = RUNS / spec / arm / f"rep{rep}" / "run.json"
            if rj.exists():
                d = json.loads(rj.read_text(encoding="utf-8"))
                c = float((d.get("usage_actual") or {}).get("cost_usd") or 0)
                if c > 0:
                    got[(spec, arm)] = (c, d.get("accepted"))
    if not got:
        continue
    pairs = sum(1 for s in specs if (s, "B") in got and (s, "C") in got)
    split = sum(1 for s in specs if ((s, "B") in got) != ((s, "C") in got))
    none = len(specs) - pairs - split
    cost = sum(v[0] for v in got.values())
    acc = sum(1 for v in got.values() if v[1])
    tot_cost += cost
    tot_pairs += pairs
    if pairs == len(specs):
        done_reps += 1
    print(f"{rep:<5}{len(got):>6}{pairs:>5}{split:>6}{none:>6}{cost:>10.2f}"
          f"{f'{acc}/{len(got)}':>8}")

print()
print(f"完了した反復: {done_reps} / {REPS}")
print(f"成立した対  : {tot_pairs} / {REPS * len(specs)}")
print(f"累計費用    : ${tot_cost:.2f}")
if done_reps:
    print(f"14反復換算  : ${tot_cost / max(tot_pairs, 1) * REPS * len(specs):.0f}")
