# 現在地（2026-08-25）— 再開時はまずこれを読む

> `GAPS_2026-08-04.md` は**この時点より古い**。A11・CT・R1・R2・R3・R8 は完了済み。
> 本書が現在の正本。`GAPS_2026-08-04.md` の §D（クリティカルパス）と §E（分析）は
> 依然として有効なので、そちらも読むこと。

## 一行で

**S6（本実験）の準備がすべて終わった。残るは S6 の実行 → 執筆 → 再現パッケージ。**

## 完了したもの（再実行しないこと）

| 項目 | 状態 | 成果物 |
|---|---|---|
| A11 per-turn 計装 | ✅ | `stream_json=True` で `--output-format stream-json --verbose`。`num_turns` / `peak_context_tokens` / `turns` が calls.jsonl に入る。検証 `probes/verify_a11.py` |
| CT（Contended）仕様 | ✅ | `benchmarks/CONTENDED_DESIGN.md`、受入テストは square-media `6f5b695`、レーン 1×3 を機械検証 |
| CT 単独パイロット | ✅ | `runs/CT_PILOT_2026-08-24.md`（n=1）。B=$0.959/98.1s、C=$1.208/178.5s、両者 19 passed |
| C′（予算付きレーン） | ❌ **park** | CT で H\* < 42.5k と判明。レーン先頭終了時点で H≈42.5k のため C′ ≡ B に縮退する。Amendment A-2 |
| R1 r̂ の確定 | ✅ | `analysis/model_predictions.json`（中央値 1.299、範囲 1.000〜1.558）。較正は `runs/calib`（B のみ・7仕様・$5.88） |
| R2 E1 集計 | ✅ | `analysis/e1_aggregate.py`（除外規則の機械化） |
| R3 E2 判定 | ✅ | `analysis/e2_tests.py`（H1〜H4b・ゲート構造） |
| R8 Amendment Log | ✅ | `protocol/rqs_hypotheses.md` §7 に A-1〜A-4 |
| R9 task_id 欠落 | ✅ | 並列実行下の競合だった（`fail-20260825-01`）。引数渡しへ修正＋回帰テスト |
| §1 の貢献の並べ替え | ✅ | v0.2。測定研究を主・方針評価を従 |

**分析テスト 29 件・フレームワーク 48 件がいずれも緑。**

## 次にやること

### 1. S6 本実験（最優先）

```bash
cd /home/fudo1/project/paper-session-affinity
python3 harness/run_experiment.py --specs benchmarks/specs.json \
  --reps 14 --label main --stream-json
```

- **規模**: 7仕様 × 2アーム × 14反復 = **196ラン**、概算 **$220**、14窓・4〜5日
- **1窓 = 1反復（14ラン）で自分から止める。** 上限に当たると対が割れる
- **同じ対（同一 spec の B と C）は必ず同じ窓に収める。** 反復が別窓なのは可
- 中断したら同じコマンドに `--skip-done` を付けて再開
- 実行後: `python3 analysis/e1_aggregate.py main` → `python3 analysis/e2_tests.py main`

### 2. 執筆（S6 と並行可能）

未着手の節: **§4 実行モデル / §5 Implementation / §7 負の結果 / §8 Threats / §9 / Abstract**。
§4・§5 は結果に依存しないので S6 の前でも書ける。

### 3. 再現パッケージ

## 絶対に忘れてはいけない制約

1. **`protocol/` は FROZEN。** 判定規則・マージン・指標・除外規則を変更しない。
   変更が要るなら §7 Amendment Log に日付と理由を書く。本実験開始後は追記も禁止。
2. **r̂ は確定済み。** 実測を見てから予測を作り直すことは禁止（§3.8.4）。
3. **分析スクリプトは実データで調整しない。** 検証は合成データのみ（`analysis/tests/`）。
4. **部分成立は部分成立のまま報告する。** スピンしない（§4）。
5. **効果は帰無の公算が高い。** 検出力は d=20% 用で、実効果は 6〜8% 程度と見込まれる
   （`GAPS_2026-08-04.md` §E1）。§1 v0.2 は帰無でも成立する構成にしてある。

## 作業上の落とし穴（記録済み。再発させない）

| 落とし穴 | 記録 |
|---|---|
| `git add -A` で他者の未コミット作業を巻き込む | `fail-20260825-02` |
| 並列経路で `self.*` の可変フィールドに実行文脈を置く | `fail-20260825-01` |
| シェル経由の Python ヒアドキュメントで引用符が崩れる | `fail-20260825-03` |
| `docs/lessons/*.jsonl` の ID を採番前に確認しない | `fail-20260825-04` |
| `calls.jsonl` の `iso` を開始時刻と誤読する（完了時刻） | `fail-20260803-03` |

## 主要な実測（論文の §3.2 に反映済み）

- 【A1】プロセス間の共有プレフィックスはキャッシュされない（γ=1、n=3）
- 【A3】resume warm は履歴全量が cache_read、費用比 中央値 1/11.1（n=3）
- 【A4】CLI 固定文脈 S ≈ 21.6k は別セッション間でキャッシュされる
- 【A5】resume が作ったキャッシュに後続の fresh がヒットしうる → nonce で遮断済み
- 【A6】cache_write は H とともに増えない（turn2 以降は新規分ちょうどで一定）。
  初回 resume の書き直しは**サイズではなく init 時点の CLI キャッシュ状態**で決まる
- 【M2】公称 TTL 5分は下限保証。実測で約10.2分まで warm
- **CT の中心的観察**: resume はターン数を 13→7 に減らすが、1ターンあたり文脈が
  倍増するため費用は +35.5%。**費用 ≈ ターン数 × 1ターンあたり文脈**
