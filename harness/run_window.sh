#!/usr/bin/env bash
# S6 本実験を1窓（1反復）だけ流す。
#
#   ./harness/run_window.sh <rep番号>
#
# 1窓＝1反復で自分から止める。上限に当たると対が割れるため、
# 全反復を一度に流さない（STATUS.md）。
#
# 中断時の扱い（2026-08-28 の実測に基づく）:
#   3並列のアームBで一過性の 429 が出ると、フレームワークは
#   .mk2/quota_state.json へ 60分の遮断を書き込む。その結果 以降の全タスクが
#   「all agent providers exhausted by quota」で失敗し、窓ごと落ちる。
#   実際には API はすぐ回復しており、再実行すれば通る。
#
#   さらに QUOTA_PATTERNS には裸の "429" が入っており、returncode != 0 のとき
#   stdout 全体を部分一致で走査する。--stream-json の stdout は20万文字規模なので、
#   トークン数や ID に "429" が含まれるだけで誤検知しうる。
#
#   よって中断時は「API が本当に落ちているか」を直接叩いて確認し、
#   生きていればローカル遮断だけを消して再開する。落ちていれば待つ。
#
# 対の分割（rc=3）は自動再開しない。人間の判断が要る。
set -u
REP="${1:?rep番号を指定すること}"
cd "$(dirname "$0")/.." || exit 1
QUOTA="$HOME/project/旧agent-framework/.mk2/quota_state.json"
MAX="${MAX_ATTEMPTS:-6}"

api_alive() {
  timeout 90 claude --print --output-format json "ping" 2>/dev/null \
    | python3 -c 'import sys,json;d=json.load(sys.stdin);sys.exit(0 if d.get("is_error") is False else 1)' \
    2>/dev/null
}

for attempt in $(seq 1 "$MAX"); do
  echo "════ rep${REP} 起動 ${attempt}/${MAX}  $(date +%H:%M:%S) ════"
  python3 -u harness/run_experiment.py \
    --specs benchmarks/specs.json \
    --reps "$REP" --label main --stream-json \
    --skip-done --cooldown-min "${COOLDOWN_MIN:-0}" --workdir /tmp/paper_main
  rc=$?

  if [ "$rc" -eq 0 ]; then
    echo "════ rep${REP} 完走  $(date +%H:%M:%S) ════"
    exit 0
  fi

  if [ "$rc" -eq 3 ]; then
    echo "════ 対の分割を検出。人間の判断が要る（自動再開しない）════"
    exit 3
  fi

  echo "---- 中断 rc=${rc}。API の生死を直接確認する ----"
  if api_alive; then
    echo "     API は生きている。ローカル遮断だけを消して再開する。"
    printf '{"providers": {}}\n' > "$QUOTA"
    sleep 30
  else
    echo "     API が応答しない。15分待つ。"
    sleep 900
  fi
done

echo "════ ${MAX}回とも進まなかった。人手で原因を見ること ════"
exit 1
