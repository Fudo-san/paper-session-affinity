# 再現パッケージ

本実験（S6）を第三者が再現するための手順。

> **正直な前置き**: 本実験は**変更不能な商用API（Claude Code CLI）の実測**である。
> プロバイダ側のキャッシュ挙動・レート制限・モデル更新は制御できず、公開もされていない。
> したがって**数値の完全な再現は保証できない**。再現できるのは
> (1) 分析の完全な再実行（データ同梱）、(2) 実験手順、(3) 判定の機械適用、である。

## 1. 何が含まれるか

| ディレクトリ | 内容 | 再現に必要 |
|---|---|---|
| `protocol/` | 事前登録（FROZEN v1.0 + Amendment Log） | 判定規則の正本 |
| `benchmarks/` | 7仕様の定義・plan.json・形状の写像 | 実験の入力 |
| `analysis/` | E1（集計）/ E2（判定）/ 統計プリミティブ / 予測 r̂ | 分析の全体 |
| `runs/main/` | **196ランの生データ**（run.json + calls.jsonl） | 分析の再実行に十分 |
| `run_ledger_main.csv` | 全 run の状態台帳（追記のみ・改変禁止） | 除外規則の監査 |
| `harness/` | 実験ドライバ・窓単位の実行器 | 実験の再実行 |
| `probes/` | M1〜M7 プローブ（キャッシュ挙動の定点観測） | §3 の実測アンカー |
| `drafts/` | 本文ドラフト | — |

## 2. レベル1: 分析だけを再現する（外部依存なし・数分）

**同梱データだけで完結する。** API もハーネスも対象リポジトリも要らない。

```bash
python3 analysis/e1_aggregate.py main     # 除外規則を機械適用 → e1_dataset_main.json
python3 analysis/e2_tests.py main --acknowledge-stop A-6   # 判定 → e2_results_main.json
```

`--acknowledge-stop A-6` が要る理由は `protocol/rqs_hypotheses.md` §7 の A-6 を参照。
E1 は停止条件（インフラ起因の再実行率 20% 超）を検出し、既定では判定を出さない。
記録済みの再開判断を明示したときだけ通る設計で、判定結果に Amendment ID が刻まれる。

統計プリミティブの検証（**合成データのみ。実データで調整していない**）:

```bash
python3 -m pytest -q analysis/tests/     # 29 tests
```

副次の感度分析（`exclusion_rules` §5 が副次に限って許可）:

```bash
python3 analysis/sensitivity.py          # ct_library 除外・離隔層除外
python3 analysis/pair_gaps.py            # 対内の B/C 実行間隔
```

期待される出力は `drafts/sec6_results.md` と `drafts/sec8_threats.md` の表と一致する。

## 3. レベル2: 実験を再実行する（API とリポジトリが要る）

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

- **プロバイダ側のキャッシュ挙動**: 公称 TTL 5分は下限保証にすぎず、
  実測で約10.2分まで warm だった（M2）。この値は時期依存でありうる。
- **モデル・CLI バージョン**: 本実験は `claude-sonnet-5` / CLI `2.1.247` の単一層。
  他バージョンでの一致は保証しない。
- **利用上限の周期と閾値**: 契約・時期に依存する。
- **ρ（初回 resume の書き直し）**: init 時点のプロバイダ側キャッシュ状態で決まり、
  **クライアントから制御できない**（M7）。再現時に同じ ρ 系列にはならない。

これらは §8 に限界として記載している。

## 5. データの完全性

- `run_ledger_main.csv` は**追記のみ・改変禁止**（`exclusion_rules` §5）。
  破棄した run の行も残っている。有効データは `runs/main/*/*/rep*/run.json` 側が正。
- **事後の外れ値除外はしていない。全数を出している。**
- 落としたペアは 0。98/98 対が成立している。

## 6. 事前登録の確認方法

`protocol/` の3文書は 2026-07-31 に FROZEN v1.0 として凍結した。
**commit `fefe7c4`（2026-07-31T01:55:17+09:00）のタイムスタンプが
「データを見る前に判定規則を固定した」証明である。**

以降の変更は §7 Amendment Log に A-1〜A-6 として記録してある。
とくに A-6（停止条件からの再開）は、**B と C の比較値を見る前に**判断・記録した。
`git log` の順序で確認できる。
