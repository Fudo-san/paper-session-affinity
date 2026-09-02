# 現在地（2026-09-02）— 再開時はまずこれを読む

> 本書が作業状況の正本。判定規則は `protocol/`、確定値は
> `analysis/e2_results_main.json`、公開先と版管理は `PUBLICATION_PLAN.md` を正本とする。
> `GAPS_2026-07-31.md`、`GAPS_2026-08-04.md` と `OUTLINE.md` 内の古い状態ラベルは
> 設計履歴であり、現在の TODO ではない。

## 一行で

**S6と凍結分析は完了し、§1〜§9・Abstract・再現手順の素材は揃った。残るのは単一原稿への統合、文献最終確認、公開前監査、GitHub/Zenodo/arXiv への公開である。**

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
| S6 本実験 | ✅ | 7仕様 × 2アーム × 14反復 = 196ラン、98/98 pair、除外0、総費用 $121.26 |
| R8 Amendment Log | ✅ | `protocol/rqs_hypotheses.md` §7 に A-1〜A-6 |
| R9 task_id 欠落 | ✅ | 並列実行下の競合だった（`fail-20260825-01`）。引数渡しへ修正＋回帰テスト |
| 凍結分析 | ✅ | `analysis/e1_dataset_main.json` / `analysis/e2_results_main.json`。中心主張は不成立 |
| 本文素材 | ✅ | `drafts/sec1_introduction.md`〜`drafts/sec9_conclusion.md` と `drafts/abstract.md`。統合・引用解決は未完 |
| 再現手順 | ✅ | `REPRODUCTION.md`。分析再実行、実験再実行、限界を分離 |

**分析テスト 29 件・フレームワーク 48 件がいずれも緑。**

## 次にやること（順序固定）

1. **本文を1本へ統合する**: `drafts/` の §1〜§9 と Abstract を LaTeX 原稿へまとめ、
   表・引用・用語・節番号を通しで検査する。著者表示名と所属は本人確認まで空欄を維持する。
2. **新規性を公開直前に再確認する**: 2026-07-31 以後の関連研究を検索し、§2 の
   「存在しない」という断定を必要なら弱める。引用未解決のまま投稿しない。
3. **公開前監査を通す**: 生データの機微情報、第三者コード/出力の再配布権、LICENSE、
   絶対パス、生成物と本文の数値一致を確認する。
4. **GitHub と Zenodo を固定する**: 公開 GitHub リポジトリを更新可能な正本、
   `v1.0.0-preprint` の Zenodo snapshot/DOI を不変な引用対象とする。
5. **arXiv へ投稿する**: primary category は `cs.SE`、cross-list 候補は `cs.AI`。
   arXiv、Zenodo、GitHub の相互リンクと版番号を一致させる。

公開先、リリース順、停止ゲートの詳細は `PUBLICATION_PLAN.md` を参照。

## 絶対に忘れてはいけない制約

1. **`protocol/` は FROZEN。** 判定規則・マージン・指標・除外規則を変更しない。
   変更が要るなら §7 Amendment Log に日付と理由を書く。本実験開始後は追記も禁止。
2. **r̂ は確定済み。** 実測を見てから予測を作り直すことは禁止（§3.8.4）。
3. **分析スクリプトは実データで調整しない。** 検証は合成データのみ（`analysis/tests/`）。
4. **部分成立は部分成立のまま報告する。** スピンしない（§4）。
5. **観測済みの負の結果を上書きしない。** 費用差中央値は C−B = +5.5% で H1 は不成立。
   時間と品質の非劣性だけが成立した。「改善手法」ではなく測定研究として報告する。

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
