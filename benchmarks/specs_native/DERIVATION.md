# Sprint 17 分割の由来と規律（実験材料の derivation note）

> 作成: 2026-08-01 / 元仕様: `square-media-spec/sprint_17/project_spec.md`（BLOCKED・未実行）
> 分割: **Sprint 17-1**（自己完結・実験に使用）／ **Sprint 17-2**（実 ai-runtime 契約待ち・park）

## 1. なぜ分割するか

- Sprint 17〜20 は「spec 有・plan 無・done 無」の**真正な未実行スプリント**（実測で確認）。
  native 形式のまま Planner→Architect→Developer→Tester の実パイプラインを通せる。
- ただし Sprint 17 の一部は **実 ai-runtime の ModelGateway 契約**（canonical 命名・正式
  transport・Runtime 側 evidence）に依存し、それは未完成。そのまま投入すると
  タスクが**達成不能**になり、実験が「できないことをやらせた」測定になってしまう。

## 2. 分割規準（事前固定・形状に対して盲目）

> **17-1 に入る条件**: square-media リポジトリ内だけで実装・検証が完結する
> （ローカル定義の deterministic mock gateway に対して動く）。
> **17-2 に入る条件**: 実 ai-runtime の契約・transport・Runtime 側 evidence を要する。

- 分割は**実行可能性のみ**で行い、レーン構成・アームC への有利不利は**見ない**
  （形状は Planner が plan を生成した後に測って報告する。選ばない）。
- この境界は仕様自身が「Sprint 17開始前に許可する準備」（fail-closed stub・
  同一契約 mock test）として定義していた線とほぼ一致する。

## 3. 仕分けの明細

| 元仕様の要素 | 行き先 | 理由 |
|---|---|---|
| `model_gateway_client.py`（薄い transport 変換・fail-closed） | **17-1** | mock 相手に完結 |
| `safe_llm_runner` の安全処理と provider 実行の分離 | **17-1** | リポ内で完結 |
| summarizer / newspaper の delegated 経路接続 | **17-1** | mock 相手に完結 |
| provider/model/usage ID の DB migration | **17-1** | リポ内で完結 |
| UI 実行状態 queued/resource_waiting/running/failed/completed | **17-1** | リポ内で完結 |
| deterministic mock E2E（ネットワーク・実モデル不使用） | **17-1** | 仕様が明示要求 |
| injection block 時に Gateway を呼ばない 等の E2E 要件 | **17-1** | mock で検証可能 |
| 実 ai-runtime 契約との reconcile（canonical 命名対応） | **17-2** | 実契約が未完成 |
| 正式 transport 越えの実接続・実 Ollama smoke | **17-2** | 同上 |
| Runtime 側に policy/lease/FinalGate evidence が残ることの検証 | **17-2** | Runtime 実装待ち |
| 「外部推論費用 0 円として記録」の実測 | **17-2** | 実経路が前提 |

## 4. 製品ルールからの逸脱（正直に記録）

元仕様は「契約未確定のまま**仮 CLI・仮 endpoint・仮 import を発明しない**」と定める。
17-1 は**実験用に固定した mock 契約**をリポ内に定義するため、この製品ルールから
形式上逸脱する。正当化: 製品文脈でこのルールが守るのは「実契約とのドリフト」だが、
実験は使い捨て worktree 上で行い、成果物を製品へ還流しない。mock 契約は
**実験材料として凍結**され、製品の contract 決定を拘束しない。
（このため分割 spec は `square-media-spec/` ではなく本リポジトリに置く。
製品側へ 17-1/17-2 分割を昇格させるかは製品側の判断として残す。）

## 5. 受入判定の弱点（正直に記録）

- 受入 = 「既存 `tests/test_summarizer.py` と `tests/test_newspaper_mode.py` が green のまま」
  ＋「仕様が要求する mock E2E テストが存在し green」。
- 後者は**エージェント自身が書くテスト**であり、自作の弱いテストで通る余地がある。
  T-13xx 群のような human-owned grader と比べ受入が弱い。これは native 仕様を
  そのまま使う（= 実験者がタスクへ介入しない）ことの代償であり、§8 Limitations に記載する。
- 全 pytest green は受入に**使わない**（baseline c2e2ed7 に本スプリントと無関係な
  by-design RED / stale テストが存在するため。運用実態も spec 記載の 877 と異なる）。

## 6. 実験パイプライン（対応付き設計の維持）

Planner の出力は非決定的なので、**フルパイプラインを両アームで別々に走らせると
タスクグラフが変わり対応付き比較が壊れる**。よって:

```
① Planner→Architect を 1 回だけ実行 → plan.json を凍結（このリポに保存）
② 凍結 plan を両アームに配布し、development_phase を B / C で実行
③ 形状（レーンあたりタスク数）は凍結 plan から測って報告する（選ばない）
```

①の費用は spec ごとに 1 回で、反復数に対して償却される。
