#!/usr/bin/env python3
"""凍結物のハッシュが変わっていないことを検証する。

`protocol/` は事前登録（FROZEN v1.0）、`runs/` と `run_ledger_*.csv` は
追記のみ・改変禁止の実測データである。ライセンス整備などの作業でこれらの
内容が変わると、「データを見る前に判定規則を固定した」証跡が壊れる。

初回実行で manifest を作り、以降は差分を検出する。

  python3 analysis/verify_frozen.py            # 検証
  python3 analysis/verify_frozen.py --update   # manifest を作り直す（要注意）
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "analysis" / "frozen_manifest.json"

TARGETS = [
    "protocol/rqs_hypotheses.md",
    "protocol/exclusion_rules.md",
    "protocol/non_inferiority.md",
    "protocol/pre_pilot_decisions.md",
    "analysis/e2_results_main.json",
    "analysis/model_predictions.json",
]
GLOBS = ["runs/main/**/run.json", "runs/main/**/calls.jsonl"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def collect() -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in TARGETS:
        p = ROOT / rel
        if p.exists():
            out[rel] = sha256(p)
    for g in GLOBS:
        for p in sorted(ROOT.glob(g)):
            out[str(p.relative_to(ROOT))] = sha256(p)
    return out


def main() -> int:
    cur = collect()
    if "--update" in sys.argv:
        MANIFEST.write_text(json.dumps(
            {"note": "凍結物の SHA-256。protocol と runs は改変禁止。",
             "count": len(cur), "files": cur},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"manifest を更新した: {len(cur)} ファイル")
        return 0

    if not MANIFEST.exists():
        print("manifest が無い。初回は --update で作成すること。", file=sys.stderr)
        return 1

    old = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    changed = [k for k in old if k in cur and old[k] != cur[k]]
    missing = [k for k in old if k not in cur]
    added = [k for k in cur if k not in old]

    print(f"検証対象 {len(cur)} ファイル（manifest {len(old)} 件）")
    print(f"  変更された: {len(changed)}")
    print(f"  消えた    : {len(missing)}")
    print(f"  増えた    : {len(added)}")
    for k in changed[:10]:
        print(f"    [変更] {k}")
    for k in missing[:10]:
        print(f"    [欠落] {k}")

    if changed or missing:
        print("\n*** 凍結物が変わっている。事前登録の証跡が壊れる。 ***", file=sys.stderr)
        return 2
    print("\n凍結物は無傷。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
