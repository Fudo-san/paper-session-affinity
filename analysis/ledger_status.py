#!/usr/bin/env python3
"""台帳の進捗を表示する（completed / aborted / excluded の内訳）."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
label = sys.argv[1] if len(sys.argv) > 1 else "calib"
path = ROOT / f"run_ledger_{label}.csv"
if not path.exists():
    print(f"[ERROR] 台帳が無い: {path}", file=sys.stderr)
    raise SystemExit(1)

rows = list(csv.DictReader(path.open(encoding="utf-8")))
done = [r for r in rows if r.get("status") == "completed"]
other = [r for r in rows if r.get("status") not in ("completed", "dry_run")]

print(f"=== {path.name} ===")
print(f"completed: {len(done)}")
total = 0.0
for r in done:
    cost = float(r["cost_usd"] or 0)
    total += cost
    print(f"  {r['spec']:<18} ${cost:>6.3f}  {r['wall_s']:>7}s  accepted={r['accepted']}")
print(f"  合計 ${total:.3f}")

if other:
    print(f"\n未完了/中断: {len(other)}")
    for r in other:
        print(f"  [{r['status']}] {r['spec']}: {(r.get('notes') or '')[:90]}")
