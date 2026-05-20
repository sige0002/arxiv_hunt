# download-pdfs Specification

## Purpose

`Paper` レコード 1 件以上の PDF をローカルディレクトリにダウンロードする。
予測可能なファイル名で保存し、arXiv のレート制限を尊重する。

## Scope

スコープ内:
- 単一論文の PDF を `pdf_url` 経由でダウンロードする。
- 一括ダウンロード時にリクエスト間ディレイを入れる。
- 論文メタデータから安全かつ決定論的なファイル名を生成する。
- 既にファイルが存在する場合にダウンロードをスキップする。

スコープ外:
- PDF 中身のパース。
- ファイルをディスクに置く以上の永続化。
- CLI 入口（現状 `scripts/download_pdfs.py` は未存在。Web UI 経由の入口は
  本 capability の標準要件として
  [Requirement: Web UI ZIP bundling entry point](#requirement-web-ui-zip-bundling-entry-point)
  に規定）。

## Requirements

### Requirement: Filename derivation

ダウンロード済みファイルは以下に従って命名 SHALL:

```
{first_author_lastname}_{year}_{arxiv_id_with_separators_replaced}.pdf
```

各構成要素は以下のように計算 SHALL:

- **先頭著者の姓**: `authors` の最初の `";"` 以前の部分を取る。コンマを
  含むならコンマ以前を、そうでなければ空白区切りの最後のトークンを取る。
  結果が空なら `unknown` を用いる。
- **年**: `paper.published` の先頭 4 文字、または `unknown`。
- **arXiv id**: `paper.arxiv_id` 中の `/` と `:` を `_` に置換したもの。

生のファイル名は次にサニタイズに通す SHALL:

- `[\w.\-]` にマッチしない文字を `_` に置換。
- 連続する `_` を 1 個に縮約。
- 先頭と末尾の `_` および `.` を除去。
- 長さが 250 文字を超える場合は 246 に切り詰めて `.pdf` を再付与。
- サニタイズ結果が空なら `paper.pdf` にフォールバック。

#### Scenario: Simple author

- **GIVEN** `authors="Yann LeCun"`, `published="2026-05-12"`,
  `arxiv_id="2605.01234v1"` の論文
- **WHEN** ファイル名を生成する
- **THEN** ファイル名は `LeCun_2026_2605.01234v1.pdf` SHALL

#### Scenario: "Last, First" author format

- **GIVEN** `authors="Vaswani, Ashish; Shazeer, Noam"` の論文
- **WHEN** ファイル名を生成する
- **THEN** 先頭セグメントは `Vaswani` SHALL

### Requirement: Skip-existing behavior

`skip_existing=True`（デフォルト）のとき、ダウンローダは対象ファイルが既に存在することを検出 SHALL し、HTTP リクエストを行わずにその `Path` を返す SHALL。
`skip_existing=False` の場合、既存ファイルは上書き SHALL。

### Requirement: Missing PDF URL

`Paper` の `pdf_url` が空の場合、本 capability は警告をログ出力 SHALL し、
ネットワークリクエストを試みず SHALL NOT、その論文について `None` を返す SHALL。

### Requirement: Rate limiting in batch mode

バッチモード（`download_papers_pdf`）では、本 capability は連続するダウンロード試行の **間** に `rate_limit` 秒（デフォルト `ARXIV_RATE_LIMIT_SECONDS = 3.0`）スリープする SHALL。
リスト末尾の論文の後にはスリープしない SHALL。`rate_limit` が `0` 以下ならスリープを無効化 SHALL。

#### Scenario: 3 papers downloaded with rate limit

- **GIVEN** 有効な `pdf_url` を持つ論文 3 件と `rate_limit=3.0`
- **WHEN** `download_papers_pdf` を呼び出す
- **THEN** 3 秒スリープがちょうど 2 回発生 SHALL — 論文 1→2 と 2→3 の間
- **AND** 論文 3 の後にスリープは発生しない SHALL

### Requirement: Failure tolerance in batch mode

単一論文での失敗（ネットワークエラー、URL 欠損 など）はバッチ全体を中断 SHALL NOT。
返却リストは失敗した論文の位置に `None` を入れて入力順を保つ SHALL。

### Requirement: Output directory creation

設定された出力ディレクトリ（デフォルト `data/pdf/`）が存在しない場合、本 capability はダウンロード前に（親ディレクトリ含めて）作成 SHALL。

### Requirement: Web UI ZIP bundling entry point

Streamlit Web UI は結果リスト（Search ページおよび History ページ）から `Download PDFs (ZIP)` ボタンとして本 capability を露出 SHALL。ボタンは現在 `st.session_state["papers"]` に保持されている `Paper` リストを入力とし、メモリ上に構築された ZIP バイト列を `arxiv_results_pdfs.zip` というファイル名で `st.download_button` からダウンロードさせる SHALL。

サーバ側の挙動は以下 SHALL:

- 既存の `download_papers_pdf(papers, output_dir=PDF_OUTPUT_DIR,
  rate_limit=ARXIV_RATE_LIMIT_SECONDS, skip_existing=True)` を **そのまま**
  呼び出す。`data/pdf/` ディレクトリを共有キャッシュとして使い、
  既に存在する PDF は再ダウンロードしない
  （[Requirement: Skip-existing behavior](#requirement-skip-existing-behavior) に従う）。
- 返却された `list[Optional[Path]]` の各エントリについて、`Path` であれば
  `make_pdf_filename` が生成した決定論的ファイル名をそのまま ZIP メンバ名
  として `zipfile.ZipFile` に追記 SHALL。
- 失敗（`None`）したエントリは ZIP からスキップ SHALL し、バッチ全体は
  止めない SHALL — 既存の
  [Requirement: Failure tolerance in batch mode](#requirement-failure-tolerance-in-batch-mode)
  をそのまま継承する。
- ZIP には末尾に `summary.txt` を 1 つ含める SHALL。中身は
  「成功 N 件 / 失敗 M 件 / 失敗 arxiv_id のリスト」をプレーンテキストで
  記述する。
- ZIP は `zipfile.ZIP_DEFLATED` で圧縮 SHALL。
- ボタン押下中は `st.spinner` を表示 SHALL し、ダウンロード対象件数と
  推定待ち時間（`件数 * ARXIV_RATE_LIMIT_SECONDS` 秒、キャッシュヒット分は
  目安）を `st.info` に出す SHALL。

新規の永続化やレートリミット定数は導入 SHALL NOT — 既存の
`download_papers_pdf` と `ARXIV_RATE_LIMIT_SECONDS` をそのまま使う。

#### Scenario: ZIP includes deterministic filenames

- **GIVEN** `papers` に `authors="Yann LeCun"`, `published="2026-05-12"`,
  `arxiv_id="2605.01234v1"`, `pdf_url="https://arxiv.org/pdf/2605.01234v1"`
  の論文 1 件
- **AND** `data/pdf/LeCun_2026_2605.01234v1.pdf` が既に存在する
- **WHEN** ユーザーが `Download PDFs (ZIP)` を押す
- **THEN** HTTP リクエストは発生しない SHALL（`skip_existing=True`）
- **AND** ダウンロードされる ZIP は `LeCun_2026_2605.01234v1.pdf` を
  ちょうど 1 件含む SHALL
- **AND** ZIP は `summary.txt` を含み、`success=1 / failed=0` を示す SHALL

#### Scenario: Missing pdf_url is skipped, batch continues

- **GIVEN** `papers` に 3 件: 1 件目は有効な `pdf_url`、2 件目は `pdf_url=""`、
  3 件目は有効な `pdf_url`
- **WHEN** ユーザーが `Download PDFs (ZIP)` を押す
- **THEN** 2 件目はネットワーク呼び出しなく `None` 扱いとなり、ZIP からは
  除外される SHALL
- **AND** ZIP には 1 件目と 3 件目の PDF が含まれる SHALL
- **AND** `summary.txt` は `failed=1` と、2 件目の `arxiv_id` を列挙
  する SHALL

## Implementation status (informational)

`arxiv_hunt/downloader.py` は実装済みかつユニットテストもある。Streamlit
Web UI は結果リストの `Download PDFs (ZIP)` ボタンから本 capability を
標準呼び出し元として使う
（[Requirement: Web UI ZIP bundling entry point](#requirement-web-ui-zip-bundling-entry-point)）。
`Plan.md` で言及されている `scripts/download_pdfs.py` は依然として未存在で、
追加するのは純粋に追加作業であり要件を **拡張** するもの。

## Implementation pointers

- `arxiv_hunt/downloader.py` — `make_pdf_filename`,
  `download_paper_pdf`, `download_papers_pdf`。
- `arxiv_hunt/config.py` — `PDF_OUTPUT_DIR`, `ARXIV_RATE_LIMIT_SECONDS`。
- Tests: `tests/test_downloader.py`。
