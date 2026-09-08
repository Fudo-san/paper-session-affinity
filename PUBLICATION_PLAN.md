# 公開計画と文書整合の正本

更新日: 2026-09-09
状態: **GitHub 公開済み（2026-09-07）／Zenodo DOI 取得済み（2026-09-08）／arXiv は保留**

## 1. 選定結果

| 対象 | 選定 | 役割 |
|---|---|---|
| 論文タイトル | *The Cost of Session Continuation in Multi-Agent Code Generation: A Measurement Study of a Commercial Coding-Agent CLI* | 負の結果を隠さず、測定研究として位置づける。2026-09-08に affinity から continuation へ変更（下記） |
| 更新可能な正本 | 公開 GitHub repository `paper-session-affinity` | **先行して公開する。** issue、訂正、後続版を管理 |
| 不変アーカイブ | Zenodo | 取得済み。`v1.2.2-preprint` snapshot に DOI を付与（2026-09-08） |
| Preprint | arXiv、primary `cs.SE` | **保留。** endorsement を確保できないため現時点では投稿しない |
| Cross-list | `cs.AI` 候補 | arXiv 投稿が可能になった場合の候補。最終可否は arXiv 側の分類に従う |
| 査読会議・誌 | preprint 後に選定 | 新着文献確認と英語原稿の完成後に別判断する |

GitHub、Zenodo、arXiv は競合する選択肢ではない。GitHub は変化する作業正本、Zenodo は
論文が参照する固定 artifact、arXiv は読まれる論文本文を担当する。

arXiv は新規投稿者に対し、当該カテゴリの既存投稿者による endorsement を求める。所属機関の
メールアドレスによる自動免除の対象でなく、推薦者の当てもないため、2026-09-07 に本人が
**arXiv を保留し GitHub 公開を先行させる**と決めた。arXiv を取り下げたのではなく、
endorsement を得る手段ができた時点で再開する。Zenodo は endorsement も実名も要求しない
ので、GitHub 公開後にそのまま進められる。

### 題名を変更した理由（2026-09-08）

当初の英語題名は *The Economics of Session Affinity...* だった。リポジトリ名 `paper-session-affinity` と
同じく、2026-07-05の企画時の位置づけ（「単純なセッション親和性方針の限界を示す測定研究」）に由来する。

しかし本文はこの語を使っていない。`main.tex` で「親和性」が現れるのは §2.3 の2箇所だけで、
そこはサービング層の親和性ルーティングと本稿を**区別するため**に使っている。
和文題名と柱書きは一貫して「セッション継続」であり、英語題名だけが本文の避けた語を掲げていた。
*Economics* も、単一言語・単一リポジトリ・単一CLI版という §8.1 の限界記述に対して大きい。

そこで英語題名を *The Cost of Session Continuation...* へ変更し、本文・和文題名・柱書きと語を揃えた。
和文題名は変更していない（元から「継続」である）。

リポジトリ名 `paper-session-affinity` は変更しない。既に公開済みで3つのタグから参照されており、
改名するとURLが切れる。企画時の語を保存していること自体は、事前登録研究では記録として意味がある。

## 2. 公開メタ情報

- Title: 上記で固定
- Author display name: **Fudo**（2026-09-07 に本人が決定。単一名で用いる）
- Affiliation: **未設定**。`Independent Researcher` を使う場合も本人確認が必要
- ORCID: 任意。未使用
- 連絡先メール: **未設定**。本人が明示的に選ばない限り論文 metadata に記載しない
- Repository URL: <https://github.com/Fudo-san/paper-session-affinity>（2026-09-07 作成）
- Release tag: `v1.2.2-preprint`（GitHub Release として公開したのはこの版のみ）
- Zenodo DOI（concept、引用にはこちら）: **10.5281/zenodo.22663555**
- Zenodo DOI（version `v1.2.2-preprint`）: **10.5281/zenodo.22663556**（2026-09-08 取得）
- arXiv ID: **TBD — submission 後に確定**
- Primary category: `cs.SE`
- Cross-list candidate: `cs.AI`

Git の `user.name` や `user.email` は commit 用のローカル設定であり、公開名・連絡先への同意とは
みなさない。メールアドレスは本人が明示的に選ばない限り論文 metadata に転記しない。

## 3. 文書の優先順位

矛盾した場合は次の順で解決する。

1. `protocol/` と `analysis/PRE_ANALYSIS_DECISIONS.md` — 凍結した宣言・判断
2. `analysis/e1_dataset_main.json` / `analysis/e2_results_main.json` — 保持する旧出力
3. `paper/revision/results.json` / `ANALYSIS_PLAN.md` / `CHANGELOG.md` — 宣言と実装の不一致を開示した訂正結果
4. `paper/main.tex` — 現行本文。表・数値は訂正JSONから生成
5. `STATUS.md` — 現在の作業状態
6. `drafts/` / `GAPS_*.md` — 歴史資料

旧E2を上書きせず、旧値・訂正値・追加分析の三者を区別する。
統合改訂稿v0.3は日本語本文と英語要旨。投稿用の英語本文は2026-09-08に `paper/main_en.tex` として作成した（31ページ）。
関連文献16件の書誌と引用範囲を一次資料で確認し、CoCoderのAPI費用評価を反映した。
この引用監査は網羅的な新着文献検索の完了を意味しない。

## 4. 公開前ゲート

次の全項目が揃うまで公開しない。

- [x] 著者表示名の確定（2026-09-07: `Fudo`。`main.tex` と `CITATION.cff` に反映済み）
- [x] 所属・ORCID・連絡先メールの要否を確定
      （2026-09-08: いずれも設定しないと決めた。所属のない研究であり、連絡はissueで受ける。
      ORCIDは取得していない。プレプリントとして著者名のみで成立する）
- [x] **push 前**: commit 履歴の著者情報を確定する
      （2026-09-07に全78 commit を `Fudo <325978958+Fudo-san@users.noreply.github.com>` へ書き換え。
      tree ハッシュ不変を確認済み。`refs/original` は push 後に削除した）
- [x] **push 前**: `runs/**/calls.jsonl` の `session_id` を公開してよいか確定する
      （同梱のまま公開した。UUIDのみでprompt/response本文を含まない。公開後の撤回はできない）
- [x] §1〜§9 と Abstract を単一 LaTeX 原稿へ統合
- [x] `［要引用］`、`TBD`、未解決の節番号・図表参照をゼロにする
      （2026-09-09: 現行文書から解消。`arXiv ID: TBD` は保留中の事実であり残す。
      `paper/revision/original/` と `drafts/` は歴史資料として当時のまま保持する）
- [x] 2026-07-31 以後の新着文献を再検索し、新規性の断定を再検査
      （2026-09-09: arXiv 12件を一次照合し、うち7件を§1・§2・§6.7へ反映。
      「履歴を渡せば再探索が減る」「履歴継承が費用を増えうる」「補助LLM呼び出しが費用を生む」は
      いずれも既知として先行研究に帰属させ、新規性の記述を測定対象の差へ限定した。
      系統的レビューではなく、新規性の不存在証明でもない）
- [x] 生データに秘密・個人情報・非公開リポジトリ内容がないことを確認
      （2026-09-08: 公開430ファイルを全走査。実名・メール・鍵・IP・住所いずれも0件。
      非公開リポジトリ由来の応答本文4件を検出し v1.0.1 で伏せた。`THIRD_PARTY_NOTICES.md` §3.1）
- [x] 第三者コード、CLI出力、対象リポジトリ由来情報の再配布権を確認
      （2026-09-08: ハーネスと対象リポジトリはライセンス未設定のため同梱・公開しないと決定済み。
      CLI出力は指標とツール名のみで、応答本文は v1.0.1 で除去した。`THIRD_PARTY_NOTICES.md` §3・§3.1）
- [x] LICENSE を確定（2026-09-08: 現状のまま確定。コードにMIT、文書とデータにCC BY 4.0。
      `REUSE.toml` と `LICENSES/` で対応を明示済み。分割は変更しない）
- [x] `CITATION.cff` を著者名・DOI・release URL 確定後に追加
      （2026-09-09: 著者 Fudo、concept DOI 10.5281/zenodo.22663555、
      version `v1.2.2-preprint`、date-released 2026-09-08 を記載）
- [x] 絶対パスは「実験記録として保持」か「可搬化」のどちらかをファイルごとに決める
      （2026-09-08: 全件を**実験記録として保持**と決めた。`/home/fudo1` は実行時の実パスであり、
      書き換えるとログが実行事実と食い違う。`benchmarks/build_specs.py` は環境変数
      `PAPER_HARNESS_REPO` で上書きでき、可搬性はそこで担保する）
- [x] 196 run / 98 pair / dropped 0 / model / CLI / 総費用が本文と artifact で一致
      （2026-09-08: 本文はアーム別に `58.35 / 62.91 USD` と表示する。合計 121.26 は印字しない。
      分割表記のほうが情報量が多いため、照合対象をアーム別の値に改めた）
- [x] リリース候補の clean checkout で分析テスト43件と凍結分析を再実行
      （tag `v1.0.0-preprint` の checkout、および公開後の GitHub からの clone で通過）
- [x] commit、release tag、E2 JSON、paper source の SHA-256 manifest を生成
      （`RELEASE_MANIFEST.json` 430件。`make_release_manifest.py` で再生成でき、
      commit SHA は注釈付きタグ `v1.0.0-preprint` が本ファイルのハッシュ経由で固定する）

### 現時点の監査結果

- API token、Bearer token、GitHub token に見える文字列: tracked files から未検出
- ハードコードされたローカルパス: `benchmarks/specs.json`、`benchmarks/smoke_specs.json`、
  `probes/verify_a11.py` に存在。実験記録と可搬用テンプレートを分離する必要がある
- `calls.jsonl`: usage、モデル、session_id、task_id、時間等の構造化計測値で、prompt/response
  本文のキーはない。ただし session_id を公開してよいかは最終監査で再確認する
- repository remote: <https://github.com/Fudo-san/paper-session-affinity>。2026-09-07 に公開済み
- `probes/*.jsonl`: 監査の対象から漏れていた。公開後の再走査で `m5_results.jsonl` に応答本文4件が
  残っていたことが分かり、v1.0.1 で伏せた。経緯は `THIRD_PARTY_NOTICES.md` §3.1。
  監査は「本実験のログ」ではなく「追跡される全ファイル」を対象にする
- LICENSE: MIT / CC BY 4.0 のファイルは存在。最終再配布監査は未完

## 4.1 リリース識別（2026-09-07）

- Repository: <https://github.com/Fudo-san/paper-session-affinity>
- Branch: `main` / Tag: `v1.0.0-preprint`
- Commit: `51c40afb75cf6801b1e04e82624dbe9e63c7cec9`
- `RELEASE_MANIFEST.json` sha256: `0399c19dc726aee63aff22a6a6c0ba66d3e9ae1a6af036b0ebfbcc686ce62532`
  （注釈付きタグ本文に記録。タグ→commit→manifest→データの鎖になる）
- 公開後に GitHub から clone して照合した: manifest 430件一致、テスト43件通過、凍結398件無傷、
  `results.json`・生成物・ソースZIPの再生成が公開版と一致。

### Zenodo へ渡すメタ情報

`.zenodo.json` をリポジトリ直下に置く。これが無いと Zenodo は GitHub のログイン名や
リポジトリ説明からメタ情報を推測し、著者名が `Fudo-san` になる。
題名・著者名・ライセンス・種別・キーワードを明示し、再現の非対称と分割ライセンスも
description に書く。Zenodo はリリース時のアーカイブに含まれる版を読むので、
このファイルは公開するタグの中に無ければ効かない。

## 5. リリース順

1. 本文統合・引用・権利監査を完了し、候補 commit を固定する。
2. **push 前に commit 履歴の著者情報を確定する。** 全 commit が個人のメールアドレスを
   保持しており、public 化すると恒久的に露出する。push 後の書き換えでは取り消せない。
3. GitHub の公開 repository を作り `origin` を設定して push する。
4. Git tag/release `v1.0.0-preprint` を作る。
5. Zenodo 連携または deposit を行い、snapshot の DOI と Git commit/tag を照合する。
6. DOI を `CITATION.cff` と README へ反映する。snapshot 自体は置き換えず、新版は新しい
   release/version として発行する。
7. arXiv は endorsement を確保できた場合のみ。TeX source を投稿し、Zenodo DOI と GitHub の
   exact tag を参照する。取得した arXiv ID を GitHub/Zenodo の metadata へ追記する。

## 6. 運用根拠

- arXiv Submission Guidelines: <https://info.arxiv.org/help/submit/index.html>
- GitHub releases: <https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases>
- GitHub + Zenodo DOI: <https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content>
- GitHub `CITATION.cff`: <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files>
- Zenodo quick start: <https://help.zenodo.org/docs/get-started/quickstart/>

## 7. 同一性ガード

公開単位は「現在の branch」ではなく exact Git tag とする。manifest には少なくとも次を含める。
実装は `make_release_manifest.py` と `RELEASE_MANIFEST.json`（430件）である。
commit SHA は manifest に書けないので、注釈付きタグの本文が manifest の SHA-256 を保持する。
これによりタグ→commit→manifest→データという鎖になり、どの環に触れても検出できる。

- Git commit SHA と tag
- `analysis/e1_dataset_main.json`
- `analysis/e2_results_main.json`
- `run_ledger_main.csv`
- `protocol/*.md`
- `runs/main/**/run.json` と `runs/main/**/calls.jsonl`
- paper source と生成 PDF

数値修正が必要になった場合は既存 release を上書きせず、`v1.0.1-preprint` のように新しい版を
作り、変更理由を明記する。

## 8. 外部操作の扱い

remote 作成、public 化、Zenodo deposit、arXiv submission は第三者から見える不可逆性の高い
操作である。著者名は確定したが、所属・連絡先・commit 履歴の著者情報・session_id の公開可否が
未決のため、実際の公開は人の最終確認後に行う。

アカウント作成と repository 作成はブラウザ操作を要するので本人が行う。担当AIが行うのは
push 直前までの準備、すなわち著者名の反映、履歴の書き換え、`origin` 設定、tag 作成、
manifest 生成、clean checkout での再現までとする。push そのものは、その時点で改めて
本人の指示を得てから実行する。

## 9. v0.3後の投稿先候補（2026-09-05）

現稿は測定と経験的所見を中心にする。採択可能性を数値や断言では示さない。
ESEMのSEIP等は候補となるが、実務上の文脈・含意と公募対象の一致を確認する。2026年SEIPは経験報告と陰性結果を含む実証研究を受け付けたが、5月27日の投稿締切は終了済み。次回公募の参考とする。
[公式SEIP公募](https://conf.researchr.org/track/eseiw-2026/eseiw-2026-esem---seip-track)

MSRのData and Tool Showcaseは再利用可能なデータ/ツールが主対象で、通常の測定論文の受け皿とは異なる。現稿を出すならMSRとの関係、公開資料の利用価値、外部装置非公開の制約を個別評価する。
[公式Data and Tool Showcase公募](https://2026.msrconf.org/track/msr-2026-data-and-tool-showcase-track)

追加実験は、内容の異なるCT仕様の追加、同じスケジュールでの継続有無、費用規模を揃えた陰性対照、モデル別費用と完全なターン記録を優先する。これらは次回計画であり未実施。
