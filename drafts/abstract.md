> **統合前の旧稿（2026-09-04に更新停止）。** 現行本文は [paper/main.tex](../paper/main.tex)、閲覧版は [PDF](../paper/main.pdf)。本ファイルには撤回・訂正済みの数値や説明が含まれる。修正点は [訂正記録](../paper/revision/CHANGELOG.md)を参照。元のバイト列は `paper/revision/original/` に保存。

# Abstract（ドラフト v0.1 — 2026-09-02）

## English

Session persistence may reduce repeated repository exploration in multi-agent code generation, but it also carries growing conversation histories and can serialize otherwise independent work. We first characterize the cache behavior of a commercial coding-agent CLI and derive a cost decomposition model from client-observable quantities. We then conduct a preregistered paired comparison of fresh sessions (B) and write-scope-connected lane continuation (C) across seven repository task specifications, two arms, and fourteen repetitions (196 runs; 98 pairs) using one fixed model and CLI version. Lane continuation increased median cost by 5.5%; it met neither the preregistered significance rule nor the 20% reduction threshold. Time remained non-inferior (median ratio 1.042; one-sided confidence bound 1.133 below the 1.15 margin), and acceptance-test pass rates were 100.0% for B and 99.0% for C. The model predicted cost-ratio magnitude within 25% for six of seven specifications but missed the direction for two, so its end-to-end hypothesis also failed. A contended workload dominated the aggregate result: C cost 50.6% more and was more expensive in all fourteen pairs. Session affinity alone is therefore not a general cost-reduction mechanism; practical policies must account for contention and the non-controllable cache state exposed by commercial CLIs.

## 日本語作業訳

マルチエージェント・コード生成におけるセッション継続は、リポジトリ再探索を減らしうる一方、
累積会話履歴を引き継ぎ、本来独立な作業を直列化しうる。本研究はまず商用コーディング
エージェント CLI のキャッシュ挙動を測定し、クライアントから観測可能な量によるコスト分解
モデルを導出した。次に、毎回新規セッション（B）と write-scope 連結成分によるレーン継続（C）を、
7仕様・2アーム・14反復（196ラン、98対応対）、固定モデル・固定CLIの事前登録実験で比較した。
C の費用は中央値で5.5%高く、事前登録した有意性条件と20%削減基準を満たさなかった。
時間は非劣性（中央値比1.042、片側信頼限界1.133 < 1.15）で、受入全通過率は B 100.0%、
C 99.0%だった。モデルは7仕様中6仕様の費用比を相対誤差25%以内に予測したが、2仕様で
優劣の符号を外し、端到端仮説も不成立だった。とくに競合形状では C が14対すべてで高く、
費用差中央値は +50.6%だった。したがって、セッション親和性だけでは一般的な費用削減策に
ならず、実用方針には競合形状と商用CLIが露出する非制御なキャッシュ状態の考慮が必要である。
