#!/usr/bin/env bash
# S6 本実験を <from> 〜 <to> 反復まで自走させる。
#
#   ./harness/run_campaign.sh 5 14
#
# これまで手作業だった外側のループを閉じる:
#   反復を流す → 割れた対を規約どおり処理 → 上限なら待つ → 次の反復
#
# 判断は一切代行しない。分割対の扱いは exclusion_rules §3 で
# 「対ごと（B・C両方）再実行」と事前登録済みであり、本スクリプトは
# その決定を実行するだけである。
#
# 停止条件:
#   - 指定範囲の全反復が完走した
#   - 同一反復で MAX_ROUNDS 回進捗が出なかった（人手に戻す）
set -u
FROM="${1:?開始rep}"
TO="${2:?終了rep}"
cd "$(dirname "$0")/.." || exit 1

MAX_ROUNDS="${MAX_ROUNDS:-40}"     # 1反復あたりの最大試行（5時間の壁を跨ぐため多め）
LIMIT_WAIT="${LIMIT_WAIT:-1800}"   # 上限で詰まったときの待機（秒）

pairs_done() {   # 指定 rep の成立した対の数
  python3 - "$1" <<'PY'
import json, sys
from pathlib import Path
rep = sys.argv[1]
root = Path(".")
specs_j = json.loads((root / "benchmarks" / "specs.json").read_text(encoding="utf-8"))
specs = {s["spec_id"]: s for s in specs_j["specs"]}
runs = root / "runs" / "main"


def ok(spec_id, arm):
    d = runs / spec_id / arm / f"rep{rep}"
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
    n_task = len(json.loads(Path(specs[spec_id]["plan"]).read_text(encoding="utf-8"))["tasks"])
    n_call = len([x for x in cj.read_text(encoding="utf-8").splitlines() if x.strip()])
    return n_call >= n_task


print(sum(1 for s in specs if ok(s, "B") and ok(s, "C")))
PY
}

N_SPECS=$(python3 -c 'import json;print(len(json.load(open("benchmarks/specs.json"))["specs"]))')

for rep in $(seq "$FROM" "$TO"); do
  echo "################ rep${rep} 開始  $(date +%F' '%H:%M:%S) ################"
  stalled=0
  for round in $(seq 1 "$MAX_ROUNDS"); do
    before=$(pairs_done "$rep")
    if [ "$before" -ge "$N_SPECS" ]; then
      echo "rep${rep}: 全${N_SPECS}対が成立済み"
      break
    fi

    bash harness/run_window.sh "$rep"
    rc=$?

    if [ "$rc" -eq 3 ]; then
      # 対が割れた。事前登録どおり対ごと再実行する。
      python3 harness/drop_split_pairs.py "$rep"
      continue
    fi

    after=$(pairs_done "$rep")
    echo "---- rep${rep} round${round}: 対 ${before} -> ${after} (rc=${rc}) ----"

    if [ "$after" -ge "$N_SPECS" ]; then
      break
    fi
    if [ "$after" -le "$before" ]; then
      stalled=$((stalled + 1))
      echo "     進捗なし（${stalled}回目）。${LIMIT_WAIT}秒待つ。"
      sleep "$LIMIT_WAIT"
    else
      stalled=0
    fi
  done

  final=$(pairs_done "$rep")
  if [ "$final" -lt "$N_SPECS" ]; then
    echo "################ rep${rep} が ${MAX_ROUNDS} 回で完走しなかった（対 ${final}/${N_SPECS}）"
    echo "人手で原因を見ること。"
    exit 1
  fi
  echo "################ rep${rep} 完走  $(date +%F' '%H:%M:%S) ################"
  python3 harness/progress.py
done

echo "################ 全反復 (${FROM}-${TO}) 完走 ################"
python3 harness/progress.py
