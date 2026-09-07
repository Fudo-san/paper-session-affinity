# 統合論文 v0.3 のビルド（日本語版・英語版）

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
python3 analysis/supplement_v03.py
python3 -m pytest -q analysis/tests/
.venv-figs/bin/python paper/render_assets.py
bash paper/build.sh
```

分析はPython標準ライブラリのみ。作図はNumPy / Matplotlib。
`generated/*.tex`と`figures/revision_*.pdf`は数値JSONから生成済みなので、PDFだけの再生成にはPythonは不要。
監査・追加分析の方法は `revision/ANALYSIS_PLAN.md`、結果は `revision/results.json`、v0.3追加結果は`revision/v0.3/results.json`、訂正内容は `revision/CHANGELOG.md`。

旧E1/E2の再実行は監査スクリプトが一時ディレクトリ内で行う。旧E2を元のパスへ直接再実行して凍結結果を上書きしない。

## ソースZIPと成果物ハッシュ

```bash
python3 paper/make_source_zip.py
```

`session-affinity-v0.3-source.zip`に、本文、参考文献、生成済み数値・表、6図のPDF、ビルドスクリプト、
ビルド説明、訂正記録と結果JSONを同梱する。日本語版と英語版の本文・表を両方含む。
Tectonic本体、TeXキャッシュ、旧原稿、生実験データはZIPへ含めない。

同じスクリプトが `revision/v0.3/artifact_manifest.json` の22件をハッシュし直す。
成果物ハッシュの正本はこの1ファイルだけとする。ZIPを作り直した後に本文やPDFを更新した場合は、
ハッシュが古くなるのでスクリプトを再実行する。

ZIP内のタイムスタンプは1980-01-01に固定し、図のPDFは`CreationDate`を出力しない。
同じ入力から作り直せば、ZIPも図もバイト列が一致する。release manifestのSHA-256はこれを前提とする。
実験の時刻を主張するものではなく、時計を除いているだけである。

旧v0.2は `versions/v0.2/` に、独自の `manifest.json` 付きで保存。v0.3 ZIPには追加分析JSONと方法、
コメント回答を同梱。共通の旧訂正履歴に加え `revision/v0.3/RESPONSE.md` を参照。

## 英語版

```bash
bash paper/build.sh en
```

本文は `main_en.tex`。数値マクロ・図・参考文献は日本語版と共有し、表だけ `generated/en/` の英語版を使う。
英語表は `render_assets.py` が日本語表から語彙表で導出し、CJK文字が1文字でも残ると生成時にassertで落ちる。
出力PDFにはCJKフォントを埋め込まないので、日本語グリフは描画できない。

## 目視確認用の画像

`revision/v0.3/pdf-review/` の contact シートと `extracted.txt` は、組版結果を人が見るための補助で、
PyMuPDFが要る。再生成できるので追跡しない。PDFを作り直したら中身が古くなる。
