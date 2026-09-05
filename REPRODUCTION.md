# 再現パッケージ

本実験（S6）を第三者が再現するための手順。

> **正直な前置き**: 本実験は**変更不能な商用API（Claude Code CLI）の実測**である。
> プロバイダ側のキャッシュ挙動・レート制限・モデル更新は制御できず、公開もされていない。
> したがって**数値の完全な再現は保証できない**。再現できるのは
> (1) 分析の完全な再実行（データ同梱）、(2) 実験手順、(3) 判定の機械適用、である。

## 1. 何が含まれるか

| ディレクトリ | 内容 | 再現に必要 |
|---|---|---|
| `protocol/` | 事前指定プロトコル（FROZEN v1.0 + Amendment Log） | 判定規則の正本 |
| `benchmarks/` | 7仕様の定義・plan.json・形状の写像 | 実験の入力 |
| `analysis/` | E1（集計）/ E2（判定）/ 統計プリミティブ / 予測 r̂ | 分析の全体 |
| `runs/main/` | **196ランの生データ**（run.json + calls.jsonl） | 分析の再実行に十分 |
| `run_ledger_main.csv` | 全 run の状態台帳（追記のみ・改変禁止） | 除外規則の監査 |
| `harness/` | 実験ドライバ・窓単位の実行器 | 実験の再実行 |
| `probes/` | M1〜M7 プローブ（キャッシュ挙動の定点観測） | §3 の実測アンカー |
| `paper/` | 統合本文・PDF・訂正結果・図表・ビルド手順 | 論文再生成 |
| `drafts/` | 統合前の歴史資料 | — |

## 2. レベル1: 分析だけを再現する（外部依存なし・数分）

**同梱データだけで完結する。** API もハーネスも対象リポジトリも要らない。

```bash
python3 analysis/revision_audit.py
python3 analysis/supplement_v03.py
python3 -m pytest -q analysis/tests/     # 38 tests
```

監査スクリプトは凍結ファイル398件を検証し、一時ディレクトリで旧E1/E2を再現する。
旧E2には `--acknowledge-stop A-6` を渡し、保存出力と完全一致を確認する。
元のE1/E2を元のパスへ直接再実行して保存結果を上書きしない。
宣言した相対尺度・平均差への実装訂正は `paper/revision/results.json` に別保存する。
CT除外・対内離隔の感度分析も同じ訂正尺度で収録する。元の感度分析は歴史資料として保持。
方法を実行前に記した `paper/revision/ANALYSIS_PLAN.md` と訂正履歴を参照。

図表・PDFの生成方法は `paper/BUILD.md`。ソースZIPには生成済み図表を含むが、生実験データは含まない。

## 3. レベル2: 実験を再実行する（API とリポジトリが要る）

> **本パッケージだけでは実行できない。** 下表のハーネスと対象リポジトリは
> ライセンス未設定のため**同梱も公開もしていない**（`THIRD_PARTY_NOTICES.md` §3）。
> 本節は「何をどう組んだか」の記述であり、**配布物ではない**。
> 第三者が同一構成を再現するには、同等のハーネスと、受入テストが存在し
> 実装が存在しない対象リポジトリを自前で用意する必要がある。

### 3.1 必要なもの

| | |
|---|---|
| **ハーネス** | MAS フレームワーク（本研究では `旧agent-framework`） |
| **対象リポジトリ** | `square-media`。3つのコミットを含むこと: `d4449a0` / `3be3676` / `6f5b695` |
| **CLI** | `claude` が PATH にあり認証済み。本研究では **2.1.247** |
| **費用** | 196ラン ≒ **$121**（実績） |
| **所要** | 5時間ごとの利用上限が律速。実績で**約5日** |

対象リポジトリの3コミットは、それぞれ**受入テストが存在し実装が存在しない**点である。
- `d4449a0` … 系列1（nightly カード T-1310/1311/1312/1320）
- `3be3676` … 系列2（sprint_17-1）
- `6f5b695` … 系列3（Contended）

### 3.2 配置

既定ではワークスペース隣接配置を仮定する。

```
<workspace>/
├── paper-session-affinity/   ← 本リポジトリ
├── square-media/             ← 対象リポジトリ
└── 旧agent-framework/        ← ハーネス
```

別配置なら環境変数で指す。

```bash
export PAPER_TARGET_REPO=/path/to/target-repo
export PAPER_HARNESS_REPO=/path/to/harness
```

### 3.3 実行

```bash
python3 benchmarks/build_specs.py         # specs.json を環境に合わせて再生成
bash harness/run_campaign.sh 1 14         # 14反復を自走（1窓=1反復で自ら止まる）
python3 harness/progress.py               # 進捗
```

`run_campaign.sh` は反復ごとに窓を回し、割れた対を事前登録どおり処理し、
上限なら待つ。判断は代行しない（対の扱いは `exclusion_rules` §3 で既に決まっている）。

## 4. 再現できないもの（明示）

- **プロバイダ側のキャッシュ挙動**: 612.1秒と916.9秒のプローブはどちらも ambiguous。厳密な保持時間は確定していない。
- **モデル・CLI バージョン**: 本実験は `claude-sonnet-5` / CLI `2.1.247` の単一層。
  他バージョンでの一致は保証しない。
- **利用上限の周期と閾値**: 契約・時期に依存する。
- **ρ（初回 resume の書き直し）**: init時点の初期cache readとの関連を観測した。確実な利用者側制御は確立できず、内部原因は未同定。

これらは §8 に限界として記載している。

## 5. データの完全性

- `run_ledger_main.csv` は**追記のみ・改変禁止**（`exclusion_rules` §5）。
  破棄した run の行も残っている。有効データは `runs/main/*/*/rep*/run.json` 側が正。
- **事後の外れ値除外はしていない。全数を出している。**
- 落としたペアは 0。98/98 対が成立している。

## 6. 事前指定の記録と限界

`protocol/` の3文書は 2026-07-31 に FROZEN v1.0 として凍結した。
commit `fefe7c4`（2026-07-31T01:55:17+09:00）と後続履歴でローカルな記録順を確認できる。
独立した公開登録時刻は検証できておらず、このタイムスタンプだけを第三者による事前登録の証明とはしない。

以降の変更は §7 Amendment Log に A-1〜A-6 として記録してある。
とくに A-6（停止条件からの再開）は、**B と C の比較値を見る前に**判断・記録した。
`git log` の順序で確認できる。

## 7. 公開版との対応

公開物は `PUBLICATION_PLAN.md` の役割分担に従う。

- GitHub: 更新可能な開発正本
- Git tag/release `v1.0.0-preprint`: 論文が参照する版
- Zenodo: 上記 release の不変 snapshot と DOI
- arXiv: 論文本文。本文中または metadata から Zenodo DOI と GitHub tag を参照

公開前に、tag の commit、Zenodo snapshot、本文記載の commit、分析結果 JSON の SHA-256 を
同一の artifact manifest に記録する。URL や DOI の `TBD` が残る間は release-ready ではない。

## v0.3追加分析

`analysis/supplement_v03.py` が陰性対照・符号数・実質予測・費用分解を `paper/revision/v0.3/results.json` に生成する。元の主要判定を置き換えない。
料金項目の換算に用いる単価は既存較正の固定値。CLI報告額と一致する価格へフィットしない。
CTタスク分解は全28ランでrun/call集計一致を確認した範囲。全仕様の費用分解は最終run.jsonを使い、追記履歴を一律合計しない。
