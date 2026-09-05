# v0.3の追加引用確認（2026-09-05）

引用した一次資料の該当範囲と制約。文献数を増やすこと自体を目的にしない。

| キー | 一次資料 | 本稿で採用した範囲 |
|---|---|---|
| dualmap | https://arxiv.org/html/2602.06502v1 §2.2–3 | prefix親和性と負荷分散の競合、2候補への写像。著者6名を原文確認 |
| agentservesim | https://arxiv.org/html/2606.09613v1 §6.1 | 同じprogramのturnを同じengineへ固定するシミュレーション比較。hit率96.26%対92.6–93.0%、p95 JCTを1.2–5.1秒短縮。API請求費用の比較ではない。著者3名を確認 |
| rayprefix | https://docs.ray.io/en/latest/serve/llm/user-guides/prefix-aware-routing.html | PrefixCacheAffinityRouter、負荷不均衡時のPower of Two Choicesへのfallback。生きた文書、閲覧日を明記 |
| llmdprefix | https://llm-d.ai/docs/well-lit-paths/foundations/precise-prefix-cache-routing | モデルサーバのKVイベント由来の局所性スコアと負荷スコアを組合せ。ユーザーの会話履歴を統合する操作ではない |
| resumeissue | https://github.com/anthropics/claude-code/issues/42338 | taekim34が2026-04-02に記録したresume時のcache creation増加。具体的モデル/版/環境の自己報告。普及率、全版への一般化、広く信じられていることの証明には使わない |
| ccusage | https://ccusage.com/guide/session-reports | セッション別に4トークン項目と費用を表示する実務ツールの存在。費用因果効果を測る統制研究とは扱わない |
| ccusagecost | https://ccusage.com/guide/cost-modes | 表示費用を保存値から読む方法とトークン・料金表から計算する方法を区別する実務上の必要性 |
| dontbreakcache（既存、再確認） | https://arxiv.org/abs/2601.06007v2 / https://arxiv.org/html/2601.06007v2 | 実在、2026-01-31 v2、Lumerほか7名、DeepResearch Benchで3社のAPI費用・TTFT評価を確認 |

## 投稿先の確認

- ESEM 2026 SEIP: https://conf.researchr.org/track/eseiw-2026/eseiw-2026-esem---seip-track は実務の経験報告、陰性結果を含む実証研究を受け付ける。2026年の投稿締切は5月27日で終了済み。次回の公募条件の参考であり、いま投稿可能な募集としない。
- MSR 2026 Data and Tool Showcase: https://2026.msrconf.org/track/msr-2026-data-and-tool-showcase-track はコミュニティ向け再利用可能なデータ/ツールが中心であり、通常の実証論文用の受け皿ではない。公開・再利用性の制約がある現稿へ無条件に勧めない。
- 採択見込みは評価できない。非公開対象を使うことだけで主要会議が不可能とも、訂正の開示が自動的に加点になるとも断定しない。
