#!/usr/bin/env bash
# M2 1ラウンド: ギャップ {10,15,30,60}分 を並列実行（各1反復・独立セッション）
# 壁時計 ≈ 最長ギャップ（60分）+ 呼び出し時間
# 使い方: bash probes/run_m2_round.sh <round_label>
set -u
cd "$(dirname "$0")/.."
ROUND="${1:-r?}"
LOG="probes/m2_${ROUND}.log"

echo "=== M2 round=${ROUND} start $(date -Iseconds) ===" | tee "$LOG"
for G in 10 15 30 60; do
  ( python3 probes/resume_probe.py --mode gap --gap-min "$G" --reps 1 \
      >> "probes/m2_${ROUND}_gap${G}.log" 2>&1 ; \
    echo "gap${G} done rc=$? $(date -Iseconds)" >> "$LOG" ) &
done
wait
echo "=== M2 round=${ROUND} end $(date -Iseconds) ===" | tee -a "$LOG"

echo "--- verdicts ---" | tee -a "$LOG"
python3 - <<'PY' | tee -a "$LOG"
import io, json
from pathlib import Path
p = Path("probes/resume_probe_results.jsonl")
rs = [json.loads(l) for l in io.open(p, encoding="utf-8")]
v = [r for r in rs if str(r.get("label","")).endswith("_verdict") and r.get("mode")=="gap"]
for r in v:
    print(f"gap={r['gap_planned_s']/60:>4.0f}min actual={r['gap_actual_s']:>6.0f}s "
          f"verdict={r['verdict']:<10} H={r['H']:>7,} "
          f"cache_r={r.get('cache_r_resume'):>7,} cache_w={r.get('cache_w_resume'):>7,} "
          f"{r.get('iso','')[:19]}")
PY
