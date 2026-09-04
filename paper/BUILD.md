# 統合論文 v0.2 のビルド

本文: `main.tex`、参考文献: `references.bib`。日本語本文・英語要旨・全9章・付録4節。
著者名・所属・公開識別子を仮に作成していない。外部公開は別工程。

## PDFを再生成する

必要なもの:

- Tectonic 0.16.9（XeTeX/LaTeX互換、BibTeXを自動実行）
- Noto Serif CJK JP / Noto Sans CJK JP / Noto Sans Mono CJK JP
- DejaVu Serif / DejaVu Sans / DejaVu Sans Mono

リポジトリのルートで `bash paper/build.sh`。
LaTeXソースZIPを展開した場合は、展開ディレクトリで `bash build.sh`。
TectonicがPATH上にあるか、`tools/tectonic`に配置されている必要がある。
初回はTeX資材をダウンロードする。コンパイラ取得方法は https://tectonic-typesetting.github.io/book/latest/installation/ を参照。
ビルドは `main.pdf`、ログは `revision/build.log`。キャッシュは`.cache/`に置く。

Tectonicを使わない場合は、上記フォントがあるXeLaTeX環境で次の順に実行する。

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

PDFにはフォントを埋め込む。ソースからの再生成にはフォントの導入が必要。
OS・フォント版・TeX資材が異なると改行やPDFバイト列が変わりうる。

## 数値・図表も作り直す

以下は実験データを持つリポジトリ全体で行う。LaTeXソースZIPだけでは分析を再実行できない。

```bash
python3 analysis/revision_audit.py
python3 -m pytest -q analysis/tests/
.venv-figs/bin/python paper/render_assets.py
bash paper/build.sh
```

分析はPython標準ライブラリのみ。作図はNumPy / Matplotlib。
`generated/*.tex`と`figures/revision_*.pdf`は数値JSONから生成済みなので、PDFだけの再生成にはPythonは不要。
監査・追加分析の方法は `revision/ANALYSIS_PLAN.md`、結果は `revision/results.json`、訂正内容は `revision/CHANGELOG.md`。

旧E1/E2の再実行は監査スクリプトが一時ディレクトリ内で行う。旧E2を元のパスへ直接再実行して凍結結果を上書きしない。

## ソースZIP

`session-affinity-v0.2-source.zip`に、本文、参考文献、生成済み数値・表、4図のPDF、ビルドスクリプト、ビルド説明、訂正記録と結果JSONを同梱。
Tectonic本体、TeXキャッシュ、旧原稿、生実験データはZIPへ含めない。
