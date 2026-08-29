#!/usr/bin/env python3
"""片アームだけ完了した対を破棄する（対ごと再実行のため）。

  ./harness/drop_split_pairs.py <rep> [label]

事前登録 exclusion_rules.md §3:
  インフラ起因の中断は spec × rep のペア（B・C両方）を再実行する。
  無効になったのが片アームでも両方やり直す（対応維持のため）。

run_experiment.py の分割ガードは「対応を決めていない状態で進むこと」を
止めるためのものであり、決め方そのものは事前登録で決まっている。
本スクリプトはその決定を実行するだけで、判断を代行しない。
`--allow-split-pairs` を選ぶ場合はこれを使わず、交絡を Limitations に書くこと。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rep = sys.argv[1] if len(sys.argv) > 1 else None
label = sys.argv[2] if len(sys.argv) > 2 else "main"
if rep is None:
    print(__doc__)
    raise SystemExit(2)

RUNS = ROOT / "runs" / label
specs_json = json.loads((ROOT / "benchmarks" / "specs.json").read_text(encoding="utf-8"))
specs = {s["spec_id"]: s for s in specs_json["specs"]}


def valid(spec_id: str, arm: str) -> bool:
    d = RUNS / spec_id / arm / f"rep{rep}"
    rj = d / "run.json"
    if not rj.exists():
        return False
    try:
        data = json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        return False
    if float((data.get("usage_actual") or {}).get("cost_usd") or 0) <= 0:
        return False
    cj = d / "calls.jsonl"
    if not cj.exists():
        return False
    n_task = len(json.loads(
        Path(specs[spec_id]["plan"]).read_text(encoding="utf-8"))["tasks"])
    n_call = len([x for x in cj.read_text(encoding="utf-8").splitlines() if x.strip()])
    return n_call >= n_task


dropped = 0
for spec_id in specs:
    b, c = valid(spec_id, "B"), valid(spec_id, "C")
    if b == c:
        continue
    for arm in ("B", "C"):
        d = RUNS / spec_id / arm / f"rep{rep}"
        if d.exists():
            shutil.rmtree(d)
            print(f"破棄: {spec_id}/{arm}/rep{rep}  （対ごと再実行）")
            dropped += 1

if dropped == 0:
    print(f"rep{rep}: 割れた対はない")
else:
    print(f"\n{dropped} 件を破棄した。--skip-done で再開すれば対ごと取り直す。")
