# 公開計画と文書整合の正本

更新日: 2026-09-02  
状態: **公開方式は選定済み／外部公開は未実施**

## 1. 選定結果

| 対象 | 選定 | 役割 |
|---|---|---|
| 論文タイトル | *The Economics of Session Affinity in Multi-Agent Code Generation: A Preregistered Study of a Commercial Coding-Agent CLI* | 負の結果を隠さず、測定研究として位置づける |
| Preprint | arXiv、primary `cs.SE` | ソフトウェア工学上の実証研究として公開 |
| Cross-list | `cs.AI` 候補 | MAS・agent研究の読者へ到達させる。最終可否は arXiv 側の分類に従う |
| 更新可能な正本 | 公開 GitHub repository `paper-session-affinity` | issue、訂正、後続版を管理 |
| 不変アーカイブ | Zenodo | `v1.0.0-preprint` snapshot に DOI を付与 |
| 査読会議・誌 | preprint 後に選定 | 新着文献確認と英語原稿の完成後に別判断する |

GitHub、Zenodo、arXiv は競合する選択肢ではない。GitHub は変化する作業正本、Zenodo は
論文が参照する固定 artifact、arXiv は読まれる論文本文を担当する。

## 2. 公開メタ情報

- Title: 上記で固定
- Author display name: **TBD — 本人確認が必要**
- Affiliation: **TBD — `Independent Researcher` を使う場合も本人確認が必要**
- ORCID: 任意。本人が使用する場合のみ設定
- Repository URL: **TBD — 現在 remote 未設定**
- Release tag: `v1.0.0-preprint`
- Zenodo DOI: **TBD — deposit 後に確定**
- arXiv ID: **TBD — submission 後に確定**
- Primary category: `cs.SE`
- Cross-list candidate: `cs.AI`

Git の `user.name` や `user.email` は commit 用のローカル設定であり、公開名・連絡先への同意とは
みなさない。メールアドレスは本人が明示的に選ばない限り論文 metadata に転記しない。

## 3. 文書の優先順位

矛盾した場合は次の順で解決する。

1. `protocol/` — 凍結した判定規則と Amendment Log
2. `analysis/e2_results_main.json` — 機械判定された確定値
3. `drafts/sec6_results.md` — 数値の論文向け説明
4. `drafts/sec8_threats.md` — 限界と感度分析
5. `drafts/sec1_introduction.md` / `drafts/abstract.md` / `drafts/sec9_conclusion.md` — 要約
6. `STATUS.md` — 作業状態
7. `OUTLINE.md` / `GAPS_*.md` — 構成履歴・当時の判断

要約文書の数字を個別に直さず、先に E2 の出力と §6 を確認してから同期する。

### 今回解消した食い違い

| 論点 | 古い記述 | 現行判断 |
|---|---|---|
| 実験状態 | S6 実行前 / データ待ち | 196ラン・98 pairで完走、E2確定済み |
| 中心主張 | C が B より安い | H1不成立。C は費用中央値 +5.5% |
| 成立した部分 | 未定 | 時間・品質の非劣性のみ成立 |
| コストモデル | 予測成立を想定 | 大きさ6/7は許容内だが符号不一致で H4b 不成立 |
| §7 | RTK / RecursiveMAS の悪化を予定 | 両者は未測定で主張しない。実測で棄却した仮説だけを書く |
| §9 / Abstract | 未着手 | 個別ドラフト作成済み |
| 公開先 | 未定 | GitHub + Zenodo DOI + arXiv `cs.SE` を選定 |

`GAPS_*.md` は当時の判断を保存する履歴資料なので本文を現在形へ書き換えず、冒頭の
SUPERSEDED表示と正本リンクで隔離する。

### まだ統合時に解消すべきもの

| 場所 | 状態 | 処置 |
|---|---|---|
| `drafts/sec6_hypotheses.md` | 凍結前の A/D/H5 を含む旧稿 | 本文へ直接使わず、`protocol/` から §6.1〜§6.5 を作る |
| `drafts/sec3_cost_model.md` 末尾 | E/H 分布等が「データ待ち」のまま | 較正JSONから埋めるか、未報告として §8 と整合させる |
| `drafts/sec2_novelty_matrix.md` | 調査基準日が 2026-07-31 | 公開直前検索後に断定と引用を更新する |
| Introduction | `［要引用］` が残る | BibTeX と本文引用を同時に確定する |
| repository全体 | 日本語節別Markdownのみ | arXiv向け英語LaTeXへ統合し、生成PDFを照合する |

## 4. 公開前ゲート

次の全項目が揃うまで公開しない。

- [ ] 著者表示名・所属・ORCID の本人確認
- [ ] §1〜§9 と Abstract を単一 LaTeX 原稿へ統合
- [ ] `［要引用］`、`TBD`、未解決の節番号・図表参照をゼロにする
- [ ] 2026-07-31 以後の新着文献を再検索し、新規性の断定を再検査
- [ ] 生データに秘密・個人情報・非公開リポジトリ内容がないことを確認
- [ ] 第三者コード、CLI出力、対象リポジトリ由来情報の再配布権を確認
- [ ] LICENSE を確定（code と文書/data を分ける必要があるかも確認）
- [ ] `CITATION.cff` を著者名・DOI・release URL 確定後に追加
- [ ] 絶対パスは「実験記録として保持」か「可搬化」のどちらかをファイルごとに決める
- [ ] 196 run / 98 pair / dropped 0 / model / CLI / $121.26 が本文と artifact で一致
- [ ] 分析テスト29件と凍結分析を clean checkout で再実行
- [ ] commit、release tag、E2 JSON、paper source の SHA-256 manifest を生成

### 現時点の監査結果

- API token、Bearer token、GitHub token に見える文字列: tracked files から未検出
- ハードコードされたローカルパス: `benchmarks/specs.json`、`benchmarks/smoke_specs.json`、
  `probes/verify_a11.py` に存在。実験記録と可搬用テンプレートを分離する必要がある
- `calls.jsonl`: usage、モデル、session_id、task_id、時間等の構造化計測値で、prompt/response
  本文のキーはない。ただし session_id を公開してよいかは最終監査で再確認する
- repository remote: 未設定
- LICENSE: 未設定

## 5. リリース順

1. 本文統合・引用・権利監査を完了し、候補 commit を固定する。
2. GitHub の公開 repository を作り `origin` を設定する。
3. Zenodo 連携または deposit を準備し、Git tag/release `v1.0.0-preprint` を作る。
4. Zenodo snapshot の DOI と Git commit/tag を照合する。
5. arXiv に TeX source と必要ファイルを投稿し、Zenodo DOI と GitHub の exact tag を参照する。
6. arXiv ID を GitHub/Zenodo の metadata へ追記する。snapshot 自体は置き換えず、新版は新しい
   release/version として発行する。

## 6. 運用根拠

- arXiv Submission Guidelines: <https://info.arxiv.org/help/submit/index.html>
- GitHub releases: <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>
- GitHub + Zenodo DOI: <https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content>
- GitHub `CITATION.cff`: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files>
- Zenodo quick start: <https://help.zenodo.org/docs/get-started/quickstart/>

## 7. 同一性ガード

公開単位は「現在の branch」ではなく exact Git tag とする。manifest には少なくとも次を含める。

- Git commit SHA と tag
- `analysis/e1_dataset_main.json`
- `analysis/e2_results_main.json`
- `run_ledger_main.csv`
- `protocol/*.md`
- `runs/main/**/run.json` と `runs/main/**/calls.jsonl`
- paper source と生成 PDF

数値修正が必要になった場合は既存 release を上書きせず、`v1.0.1-preprint` のように新しい版を
作り、変更理由を明記する。

## 8. 現時点で外部操作をしない理由

remote 作成、公開化、Zenodo deposit、arXiv submission は第三者から見える不可逆性の高い操作である。
著者情報・権利・LICENSE が未確定のため、本書では方式の選定と公開ゲートの固定までを行い、
実際の公開は人の最終確認後に行う。
