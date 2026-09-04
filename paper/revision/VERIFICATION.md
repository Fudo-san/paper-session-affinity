# 統合改訂稿 v0.2 検証記録

実施日: 2026-09-04。対象はローカル統合成果物。公開の完了判定ではない。

- `python3 -m pytest -q analysis/tests/`: exit 0、33 passed。`tests.txt`参照。
- `python3 analysis/verify_frozen.py`: exit 0、398ファイルの変更・削除・追加はすべて0。`frozen_verification.txt`参照。
- `python3 analysis/revision_audit.py`: exit 0。旧E1/E2を一時領域で再現し保存JSONと完全一致。`legacy_reproduction.txt`、`audit_output.txt`参照。
- `bash paper/build.sh`: exit 0。Tectonic 0.16.9で本文・参考文献・図表を組版。
- 旧稿・関連文書23件のバックアップSHA-256をmanifestに照合、全件一致。
- PDFは18ページ、27フォントをすべて埋込み。リンク75件。日本語文字抽出に置換文字なし、未解決の「??」なし。
- ビルドログにOverfull、undefinedの警告なし。OSフォント参照による環境依存警告は残る。環境を変えたPDFバイト列の一致は保証しない。
- 主結果+5.51%、時間上限1.1335、受入下限-5.10ポイント、98/98・97/98をPDF抽出テキストでも確認。
- 全ページを一覧で目視し、最終改ページ後の15〜18ページも個別に確認。図表の切れ、重なり、孤立した少量本文のページを解消。
- ソースZIPはCRC検査を通過。/tmpの独立した展開先からTectonicで再ビルドしexit 0。全18ページの抽出テキストが正本PDFと完全一致（同一フォント・既取得TeXキャッシュ使用）。`source_build.log`参照。

## 範囲と残条件

比較データの再取得、商用サービスの再実験、投稿用英語本文、外部公開は行っていない。
ソースZIPは論文PDFの再生成用であり、196ランの実験再実行パッケージ全体ではない。
著者情報・公開先・DOIは未確定。投稿前の新着文献検索・権利と機微情報の最終監査は別工程。
