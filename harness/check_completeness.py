#!/usr/bin/env python3
"""全 run について「計画したタスク数だけモデルを呼べたか」を確認する。

cost>0 だけを有効性の条件にしていたため、4タスク中1タスクしか実行できなかった
run が「有効な観測」として集計に入っていた（2026-08-02 に m_mixed C rep3 で発生）。
部分実行はインフラ起因の失敗であり、観測として扱ってはならない。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "pilot2"
    specs = json.loads((ROOT / "benchmarks" / "specs.json").read_text(encoding="utf-8"))["specs"]
    want = {}
    for s in specs:
        plan = json.loads(Path(s["plan"]).read_text(encoding="utf-8"))
        want[s["spec_id"]] = len(plan["tasks"])

    print(f"{'spec':<17}{'arm':<4}{'rep':<5}{'期待':>5}{'実行':>5}{'受入':>6}{'cost':>9}  判定")
    bad = []
    for spec_id, n_task in sorted(want.items()):
        for arm in ("B", "C"):
            for rep in (1, 2, 3):
                d = ROOT / "runs" / label / spec_id / arm / f"rep{rep}"
                rj = d / "run.json"
                if not rj.exists():
                    continue
                r = json.loads(rj.read_text(encoding="utf-8"))
                cj = d / "calls.jsonl"
                n_call = 0
                if cj.exists():
                    n_call = len([x for x in cj.read_text(encoding="utf-8").splitlines() if x.strip()])
                cost = (r.get("usage_actual") or {}).get("cost_usd", 0)
                ok = n_call >= n_task
                mark = "OK" if ok else "部分実行→無効"
                if not ok:
                    bad.append((spec_id, arm, rep, n_task, n_call))
                print(f"{spec_id:<17}{arm:<4}{rep:<5}{n_task:>5}{n_call:>5}"
                      f"{str(r.get('accepted')):>6}{cost:>9.4f}  {mark}")

    print()
    if bad:
        print(f"部分実行 {len(bad)} 件:")
        for b in bad:
            print(f"  {b[0]} {b[1]} rep{b[2]}  期待{b[3]} 実行{b[4]}")
        print("\n対応: 事前登録 exclusion_rules.md により、インフラ起因なので")
        print("      **対（両アーム）を再実行**する。最大1回。")
    else:
        print("部分実行なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
