#!/usr/bin/env python3
"""パイロットから反復数 N を算出する。

手順は protocol/pre_pilot_decisions.md の決定3で先に固定してある。
対ごとの相対差 d = (C - B)/B を spec をまたいでプールし、
対応のある検定・両側 α=0.05・検出力 0.80・δ=0.20 として
N = (1.96 + 0.84)^2 * s_d^2 / 0.20^2 を切り上げる。下限5・上限20。
"""
from __future__ import annotations

import csv
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Z = 1.96 + 0.84
DELTA = 0.20
N_MIN, N_MAX = 5, 20


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "pilot2"
    ledger = ROOT / f"run_ledger_{label}.csv"
    rows = list(csv.DictReader(ledger.open(encoding="utf-8")))

    ok = [r for r in rows
          if r["status"] == "completed" and float(r["cost_usd"] or 0) > 0]
    pairs: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for r in ok:
        pairs[(r["spec"], r["rep"])][r["arm"]] = float(r["cost_usd"])

    print(f"{'spec':<17}{'rep':<5}{'B':>9}{'C':>9}{'(C-B)/B':>10}")
    ds: list[float] = []
    by_spec: dict[str, list[float]] = defaultdict(list)
    for (spec, rep), v in sorted(pairs.items()):
        if "B" in v and "C" in v:
            rel = (v["C"] - v["B"]) / v["B"]
            ds.append(rel)
            by_spec[spec].append(rel)
            print(f"{spec:<17}{rep:<5}{v['B']:>9.4f}{v['C']:>9.4f}{rel:>+9.1%}")

    if len(ds) < 2:
        print("\n対が足りない")
        return 1

    mean, sd = st.mean(ds), st.stdev(ds)
    n_raw = Z ** 2 * sd ** 2 / DELTA ** 2
    n = max(N_MIN, min(N_MAX, math.ceil(n_raw)))

    print(f"\n完成した対 n={len(ds)}")
    print(f"相対差 平均 {mean:+.1%}   SD {sd:.1%}")
    print(f"N（生値 {n_raw:.1f}）→ 採用 N = {n}")
    if math.ceil(n_raw) > N_MAX:
        print("  ※ 上限20を超えた。事前登録どおり本実験は実施せず、")
        print("    「事前登録した検出力を現実的な費用で達成できない」と報告する。")

    print("\n=== spec ごと（参考。N の決定には使わない）===")
    for spec, v in sorted(by_spec.items()):
        s = f"{st.stdev(v):.1%}" if len(v) > 1 else "—"
        print(f"  {spec:<17}n={len(v)}  平均{st.mean(v):+7.1%}  SD {s}")

    aborted = [r for r in rows if r["status"] == "aborted"]
    total = sum(float(r["cost_usd"] or 0) for r in rows)
    print(f"\n完了 {len(ok)} / 中断 {len(aborted)} / 総課金 ${total:.2f}")
    if aborted:
        print("中断時刻: " + ", ".join(r["iso"][11:19] for r in aborted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
