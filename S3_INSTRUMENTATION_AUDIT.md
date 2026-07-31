# S3 計装検証 — 結論: **現状の agent-framework では本実験を実行できない**

> 実施: 2026-07-31 / 対象: `~/project/agent-framework`（実験装置）
> 判定: **S5（パイロット）・S6（本実験）はブロック**。計装の実装が先行必須。

## 1. 何を確認したか

`protocol/rqs_hypotheses.md` §2 が要求する指標を、実際に取得できるかをコードで確認した。

| 必要な項目 | 用途 | 現状 |
|---|---|---|
| cache_read / cache_creation トークン | **RQ1 主要評価**（キャッシュ経済そのもの） | **取得なし** |
| input / output トークン（実測） | 同上 | 推定のみ |
| total_cost_usd（ベンダー報告値） | **RQ1 主要評価** | **取得なし** |
| session_id | **アームC（レーン継続）に必須** | **取得なし** |
| model ID / CLI version | §8 ドリフト統制・M1で実害を確認済み | **記録なし** |
| 壁時計時間 | RQ2 共同ゲート | 部分的（metrics に所要時間あり） |
| write-set（実測） | 副次指標・scope_drift | 未実装 |

## 2. 根拠（コード実体）

- **`mk2_backends.py` の CLI 呼び出しに `--output-format json` が無い。**
  ```
  cmd = [exe, "--print", "--allowedTools", ",".join(allowed_tools)]
  ```
  プレーンテキストしか受け取っていないため、usage・cost・session_id は**構造的に取得不能**。
- **`AgentCallResult` のフィールド**: `backend / agent_name / prompt_chars / output /
  returncode / stderr / quota_event / attempts`。usage 系は一つも無い。
- **`MetricsCollector` は推定値のみ**: `input_tokens_est = input_chars // 3`。
  **文字数からの推定では cache_read と cache_creation を原理的に区別できない。**
  本稿の主張はこの2者の単価差（α_r=0.1 vs α_w=1.25）に依存するため、推定値では検証できない。
- `calls.jsonl` / `run_manifest.json` は**存在しない**（OUTLINE §5.2 は【確定・設計済み】と
  記していたが、設計のみで実装は無い）。
- `orchestrator.py` の `mode: "fresh"|"resume"|"single"` は **Sprint の再開**であって
  セッション再開ではない。無関係。
- `cache_probe.py` は 2026-07-03 の A1 単発プローブ。実験計装ではない。

## 3. 最も重い帰結: **アームC が実装できない**

`--resume <session_id>` を使うには session_id が要る。現状は取得していないため、
**レーン継続（アームC）そのものが動かない。** B vs C の比較以前の問題である。

## 4. 必要な実装（S3' として S5 の前に置く）

1. `ClaudeCliBackend` に `--output-format json` を追加し、応答を JSON としてパースする。
   - **統合リスク**: 既存パイプラインはプレーンテキスト前提。JSON の `result` フィールドから
     本文を取り出して従来経路へ渡す必要がある。既存 107 テストで回帰を検出できる。
2. `AgentCallResult` を拡張: `input / output / cache_creation / cache_read / cost_usd /
   session_id / model`。
3. **セッション継続の実装**: session_id を保持し `--resume` で継続できるようにする（アームC の本体）。
4. `calls.jsonl`（追記専用）を出力: `iso, spec, arm, rep, task_id, agent, session_id,
   model, cli_version, input, output, cache_read, cache_creation, cost_usd, wall_s`。
5. run 単位で **CLI バージョンを記録**（M1 で 2.1.190→2.1.220 のドリフトが実際に起きた）。

## 5. ロードマップへの影響

- **S5・S6 はブロック**。上記 1〜5 が終わるまで実験は開始できない。
- S1（事前登録）・S2（プローブ）・S4（ベンチ特性化）・S7（文献）は**影響を受けない**（並行可）。
- 予定への影響: TODO の「3〜5週」見積もりは計装実装を含んでいなかった。**その分伸びる。**
- ただしこれは agent-framework を「実験装置」と位置づけた判断と整合する作業であり、
  スコープ逸脱ではない。**装置が動かなければ実験はできない**という当然の前提。

## 6. S3 の副次的な確認結果

- CLI バージョンの毎ラン記録という方針は**妥当と実証された**（M1 でドリフトが実害を出した）。
- 既知 ground truth での較正は、プローブ（`probes/resume_probe.py`）が
  usage を正しく取得できていることで**部分的に達成済み**。同じパース処理を
  agent-framework 側へ移植すればよい（新規開発ではなく移植）。
