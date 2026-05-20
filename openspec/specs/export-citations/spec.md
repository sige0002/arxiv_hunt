# export-citations Specification

## Purpose

`Paper` レコードを 1 件以上、業界標準の引用形式（BibTeX `.bib` および
RIS `.ris`）に変換し、Zotero や Mendeley などの文献管理ソフトに取り込めるようにする。

## Scope

スコープ内:
- 論文 1 件につき BibTeX `@article{…}` エントリを 1 件生成する。
- 論文 1 件につき RIS エントリを 1 件生成する。
- 複数エントリをディスク上の `.bib` または `.ris` ファイルに書き出す。

スコープ外:
- DOI 解決やジャーナルメタデータの取得（arXiv 由来情報のみを使う）。
- CLI 入口（現状未配線。Web UI 経由の入口は本 capability の標準要件として
  [Requirement: Web UI streaming download entry point](#requirement-web-ui-streaming-download-entry-point)
  に規定）。

## Citation key

BibTeX エントリの citation key は決定論的に以下のように導出 SHALL:

```
{first_author_lastname_lowercased}{publication_year}_{arxiv_id_no_dots}
```

例:
- "Ashish Vaswani et al." 著、2017 年、id `1706.03762v5`
  → `vaswani2017_170603762v5`。
- 単名著者 `"Plato"`、2026 年、id `2602.0001`
  → `plato2026_26020001`。

先頭著者がパースできない場合、姓に `unknown`、年に `0000` を用いる SHALL。

## Requirements

### Requirement: BibTeX entry shape

各 BibTeX エントリは単一の `@article{…}` ブロックとして出力 SHALL し、
以下のフィールドをこの順で含む SHALL:

1. `title`
2. `author`（セミコロン区切りの著者を `" and "` で再結合）
3. `year`（`paper.published` の `YYYY`）
4. `month`（小文字 3 文字略号。published 日付から月が読み取れない場合は
   **省略**）
5. `eprint`（バージョン付き arXiv id 全体）
6. `archiveprefix = {arXiv}`
7. `primaryclass`（`paper.primary_category`）
8. `abstract`
9. `url`（`paper.entry_url`、空なら省略）

`title` と `abstract` 中の `&`, `%`, `#`, `_`, `$` はそれぞれの前に
バックスラッシュ 1 個を置いてエスケープ SHALL。

#### Scenario: BibTeX for a multi-author paper

- **GIVEN** `authors="Ashish Vaswani; Noam Shazeer"`,
  `title="Attention is All You Need"`, `published="2017-06-12"`,
  `primary_category="cs.CL"`, `arxiv_id="1706.03762v5"` の `Paper`
- **WHEN** `paper_to_bibtex` を呼び出す
- **THEN** 出力に `@article{vaswani2017_170603762v5,` を含む SHALL
- **AND** `author` フィールドは `{Ashish Vaswani and Noam Shazeer}` SHALL
- **AND** `month = jun` フィールドが存在する SHALL（中括弧なし）

### Requirement: RIS entry shape

各 RIS エントリはタイプ `ELEC` で出力 SHALL し、以下のタグをこの順で
含む SHALL:

1. `TY  - ELEC`
2. `TI  - <title>`
3. 著者 1 名につき `AU  - <author>`（セミコロン区切りを分割）
4. `AB  - <abstract>`
5. `DA  - YYYY/MM/DD`（`paper.published` がある場合）
6. `PY  - YYYY`（`paper.published` がある場合）
7. `UR  - <entry_url or pdf_url>`（`entry_url` を優先）
8. `AN  - <arxiv_id>`
9. `paper.categories` の非空カテゴリごとに `KW  - <category>`
10. `ER  -`（エントリ終端）

#### Scenario: RIS preserves multiple authors and keywords

- **GIVEN** `authors="A; B; C"`, `categories="cs.AI; cs.LG"` の `Paper`
- **WHEN** `paper_to_ris` を呼び出す
- **THEN** 出力には `AU  -` 行が正確に 3 行、`KW  -` 行が正確に 2 行、
  入力順で含まれる SHALL
- **AND** 末尾の非空行は `ER  -` SHALL

### Requirement: Bulk file emission

`papers_to_bibtex_file` と `papers_to_ris_file` は以下を行う SHALL:

- `output_path` の親ディレクトリが無ければ作成する。
- 各エントリを 2 改行（`"\n\n"`）で連結する — 隣接エントリの間に空行 1 行。
- UTF-8 テキストとして `output_path` に書く。
- 書き出したファイルの解決済み `Path` を返す。

### Requirement: Web UI streaming download entry point

Streamlit Web UI は結果リスト（Search ページおよび History ページ）から `Download BibTeX` と `Download RIS` の 2 つのボタンとして本 capability を露出 SHALL。両ボタンは現在 `st.session_state["papers"]` に保持されている `Paper` リストをメモリ上で文字列化し、`st.download_button` で配信 SHALL。

サーバ側の挙動は以下 SHALL:

- BibTeX 出力: 各 `Paper` に対して既存の `paper_to_bibtex(paper)` を呼び、
  結果を `"\n\n".join(...)` で連結する SHALL。出力ファイル名は
  `arxiv_results.bib`、MIME は `application/x-bibtex`、エンコーディングは
  UTF-8 SHALL。
- RIS 出力: 各 `Paper` に対して既存の `paper_to_ris(paper)` を呼び、
  結果を `"\n\n".join(...)` で連結する SHALL。出力ファイル名は
  `arxiv_results.ris`、MIME は `application/x-research-info-systems`、
  エンコーディングは UTF-8 SHALL。
- 中間ディスクファイルは作成 SHALL NOT — `papers_to_bibtex_file` および
  `papers_to_ris_file` は Web UI からは呼ばない。ファイル書き出しを規定する
  既存の
  [Requirement: Bulk file emission](#requirement-bulk-file-emission)
  は CLI / プログラム的呼び出し向けに残る。
- 各エントリ単位の整形（BibTeX `@article` のフィールド順、RIS `ELEC` の
  タグ順、エスケープ規則）は既存の
  [Requirement: BibTeX entry shape](#requirement-bibtex-entry-shape) /
  [Requirement: RIS entry shape](#requirement-ris-entry-shape)
  をそのまま流用 SHALL し、本要件は **新規の整形ルールを追加しない**。

#### Scenario: BibTeX download for a single paper

- **GIVEN** `papers` に `arxiv_id="1706.03762v5"`,
  `authors="Ashish Vaswani; Noam Shazeer"`,
  `title="Attention is All You Need"`, `published="2017-06-12"`,
  `primary_category="cs.CL"` の論文 1 件
- **WHEN** ユーザーが `Download BibTeX` を押す
- **THEN** ダウンロード内容は `paper_to_bibtex(paper)` の出力と
  バイト一致 SHALL
- **AND** ファイル名は `arxiv_results.bib` SHALL
- **AND** ディスク上に中間 `.bib` ファイルは残らない SHALL

#### Scenario: RIS download concatenates multiple entries with blank line

- **GIVEN** `papers` に 2 件
- **WHEN** ユーザーが `Download RIS` を押す
- **THEN** ダウンロード内容は
  `paper_to_ris(papers[0]) + "\n\n" + paper_to_ris(papers[1])` と
  バイト一致 SHALL
- **AND** ファイル名は `arxiv_results.ris` SHALL

## Implementation status (informational)

`arxiv_hunt/bibtex.py` の関数は実装済みかつユニットテストもある。Streamlit
Web UI は結果リストの `Download BibTeX` / `Download RIS` ボタンから本
capability を標準呼び出し元として使う
（[Requirement: Web UI streaming download entry point](#requirement-web-ui-streaming-download-entry-point)）。
CLI 入口（例えば `--format bibtex` フラグ）は依然として未配線で、追加するのは
要件を **拡張** するもの。

## Implementation pointers

- `arxiv_hunt/bibtex.py` — `paper_to_bibtex`, `paper_to_ris`,
  `papers_to_bibtex_file`, `papers_to_ris_file`,
  `_make_bibtex_key`, `_escape_bibtex`。
- Tests: `tests/test_bibtex.py`。
