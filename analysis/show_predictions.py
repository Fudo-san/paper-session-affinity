#!/usr/bin/env python3
"""model_predictions.json の中身を人が読める形で表示する（R1 の確認用）."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "analysis" / "model_predictions.json").read_text(encoding="utf-8"))

print(f"較正元      : {d['calibration_source']}  (completed のみ: {d.get('completed_runs_only')})")
print(f"単価係数    : alpha_r={d['alpha_r']}  alpha_w={d['alpha_w']}")
print(f"操作的定義  : E = {d['operational_definition']['E']}")
print()

only = sys.argv[1] if len(sys.argv) > 1 else None
for spec, s in sorted(d["specs"].items()):
    if only and spec != only:
        continue
    p = s["prediction"]
    print(f"=== {spec}  r_hat={p['r_hat']}  (B=${p['total_B']} → C_pred=${p['total_C_pred']}) ===")
    print(f"  lanes: { {k: v for k, v in s['lanes'].items()} }")
    print(f"  {'task':<10}{'K':>4}{'K_E':>5}{'E_tok':>10}{'W_tok':>11}{'peak_H':>9}  edit")
    for t in s["calibration"]:
        print(f"  {t['task_id']:<10}{t['K']:>4}{t['K_E']:>5}{t['E_tokens']:>10,}"
              f"{t['W_tokens']:>11,}{t['peak_context']:>9,}  {t['edit_tool_seen']}")
    print(f"  {'task':<10}{'pos':>4}{'rho':>5}{'H_prev':>10}{'cost_B':>10}{'cost_C_pred':>13}")
    for x in p["tasks"]:
        hp = f"{x['H_prev']:,}" if x["H_prev"] else "-"
        print(f"  {x['task_id']:<10}{x['pos']:>4}{x['rho']:>5}{hp:>10}"
              f"{x['cost_B']:>10.4f}{x['cost_C_pred']:>13.4f}")
    print()
