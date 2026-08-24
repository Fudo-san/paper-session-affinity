#!/usr/bin/env python3
"""ラン単位の費用と（A11 があれば）H の軌跡を集計する.

用途:
  - 残工程の費用見積り（1ランあたり実績 × 予定ラン数）
  - C′ の要否判断: レーン内で H が H* に届くか（GAPS_2026-08-04 §E3）

使い方:
  python3 analysis/pilot_cost_summary.py runs/pilot2
  python3 analysis/pilot_cost_summary.py runs/ctpilot
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path


def load_runs(root: Path) -> list[dict]:
    runs = []
    for calls in sorted(root.rglob("calls.jsonl")):
        rows = [json.loads(l) for l in calls.open(encoding="utf-8") if l.strip()]
        if not rows:
            continue
        rel = calls.relative_to(root).parts
        runs.append({
            "spec": rows[0].get("spec") or (rel[0] if rel else "?"),
            "arm": rows[0].get("arm") or "?",
            "rep": rows[0].get("rep"),
            "rows": rows,
            "cost": sum(r.get("cost_usd") or 0 for r in rows),
        })
    return runs


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/pilot2")
    runs = load_runs(root)
    if not runs:
        print(f"[ERROR] {root} に calls.jsonl が無い", file=sys.stderr)
        return 1

    costs = [r["cost"] for r in runs]
    print(f"=== {root} ===")
    print(f"runs={len(runs)}  合計=${sum(costs):.2f}  "
          f"平均=${st.mean(costs):.3f}  中央値=${st.median(costs):.3f}")

    print("\n--- ラン別 ---")
    print(f"{'spec':<16}{'arm':<5}{'rep':<5}{'tasks':<7}{'cost':>9}")
    for r in sorted(runs, key=lambda x: (x["spec"], x["arm"], x["rep"] or 0)):
        print(f"{r['spec']:<16}{r['arm']:<5}{str(r['rep']):<5}"
              f"{len(r['rows']):<7}${r['cost']:>8.3f}")

    # --- 対（同一 spec/rep の B と C）---
    pairs: dict[tuple, dict] = {}
    for r in runs:
        pairs.setdefault((r["spec"], r["rep"]), {})[r["arm"]] = r["cost"]
    complete = {k: v for k, v in pairs.items() if "B" in v and "C" in v}
    if complete:
        print("\n--- 対の相対差 (C−B)/B ---")
        diffs = []
        for (spec, rep), v in sorted(complete.items()):
            d = (v["C"] - v["B"]) / v["B"] if v["B"] else 0.0
            diffs.append(d)
            print(f"  {spec:<16}rep{rep}  B=${v['B']:.3f}  C=${v['C']:.3f}  "
                  f"{d:+.1%}")
        if len(diffs) >= 2:
            print(f"  平均 {st.mean(diffs):+.1%}  SD {st.pstdev(diffs):.1%}")

    # --- A11: H の軌跡（C′ の要否判断に使う）---
    has_turns = any(r.get("turns") for run in runs for r in run["rows"])
    print("\n--- H の軌跡（A11） ---")
    if not has_turns:
        print("  per-turn が記録されていない（--stream-json 無しで実行された）")
        print("  → C′ の閾値判定に必要な H はこのデータからは得られない")
        return 0

    for run in sorted(runs, key=lambda x: (x["spec"], x["arm"])):
        peaks = []
        for r in run["rows"]:
            pk = r.get("peak_context_tokens")
            if pk:
                peaks.append((r.get("task_id") or "?", r.get("resumed"),
                              r.get("num_turns"), pk))
        if not peaks:
            continue
        print(f"  [{run['spec']} arm={run['arm']} rep={run['rep']}]")
        for tid, resumed, nturns, pk in peaks:
            flag = "resume" if resumed else "fresh "
            print(f"    {tid:<8}{flag}  turns={nturns:<4}peak_context={pk:>9,}")
        print(f"    → レーン内 H の最大 = {max(p[3] for p in peaks):,}")
    print("\n  判断材料: この最大 H が H*（§3.5, 概算 93k〜200k）に届かなければ、")
    print("            C′ は一度も分割せず C と同一動作になる（GAPS §E3）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
