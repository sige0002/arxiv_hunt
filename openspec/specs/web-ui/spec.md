# web-ui Specification

## Purpose

最も典型的なワークフロー — arXiv 検索、直近検索の閲覧、CSV / Excel
ダウンロード、アップロード済み CSV のオフライン Excel 変換 — を
ブラウザで操作できるフロントエンド（Streamlit）を提供する。

## Scope

スコープ内:
- 左サイドバーから選べる 4 ページ: `Search`, `History`, `Library`,
  `Excel Convert`。
- Streamlit ランチャ（`run_ui.py`）とページ設定。
- Streamlit 固有のインタラクション（フォーム、プリセット、ファイル
  アップロード、ダウンロードボタン）。

スコープ外:
- 検索・CSV・Excel のコアロジック — それぞれ
  [`search-papers`](../search-papers/spec.md),
  [`export-csv`](../export-csv/spec.md),
  [`export-excel`](../export-excel/spec.md) の責務。本仕様は UI が
  それらをどう呼び出すかのみを規定する。
- CLI コマンド（`search-papers` と `export-excel` の責務）。

## Layout

ページは `page_title="arxiv_hunt"` と `layout="wide"` で設定 SHALL。
全ページでサイドバーを描画 SHALL。サイドバーはタイトル `arxiv_hunt`、
以下 4 ページ名を持つラジオコントロール 1 つ、キャプション
`"Search arXiv papers and export to Excel."` を含む。

```
┌────────────────────┬────────────────────────────────────────────────┐
│ Sidebar            │ Main panel                                     │
│  - arxiv_hunt      │                                                │
│  - Search          │   いずれか:                                    │
│  - History         │     • 検索フォーム + 結果リスト                │
│  - Library         │     • 検索履歴（直近 CSV アーカイブ）          │
│  - Excel Convert   │     • Library (DB FTS5 / タグ / DB 履歴)       │
│                    │     • CSV → Excel 変換                         │
└────────────────────┴────────────────────────────────────────────────┘
```

## Requirements

### Requirement: Search page

Search ページは以下を順に描画 SHALL:

1. `SEARCH_PRESETS` から取ったプリセットボタン行（例: "LLM/NLP",
   "Computer Vision", "Robotics"）。プリセットクリックは query/categories
   ウィジェットを埋めてページを再実行する SHALL — 自動送信はしない
   SHALL NOT。
2. Streamlit `st.form` 名 `"search_form"`。内容は:
   - `Search query` テキスト入力、`MAX_QUERY_LENGTH` でキャップ。
   - `Author` テキスト入力。
   - `Combine query & author with` ラジオ: `AND` / `OR`、デフォルト `AND`。
   - `Start date` と `End date` 行。それぞれデフォルト「7 日前」と「今日」、
     上限は `today`（未来日不可）。
   - `Max results` 数値入力、`1..MAX_RESULTS_LIMIT`、デフォルト `10`。
   - `Categories` 複数選択（`ARXIV_CATEGORIES` から）。
   - プライマリ送信ボタン `Search`。

送信時、ページは以下を行う SHALL:

- [`search-papers`](../search-papers/spec.md) に従って入力を検証する
  （長さ、シェルメタ文字拒否、日付順序、`query.strip()` または
  `author.strip()` の少なくとも一方が非空）。エラーは `st.error` で
  インライン表示し、検索は中止する。
- `start_date` と `end_date` を使って（`days` は使わず）
  `ArxivClient.search` で検索する。
- 結果を `save_papers_to_csv` で保存し、続けて `cleanup_old_archives`
  を呼ぶ（History ページが 5 件超を表示しないようにするため）。
- 結果が非空であれば、`st.session_state["db"]` の `PaperDatabase` に対し
  `save_search(query=<人間向けラベル>, params=<フォーム入力 dict>,
  papers=<結果>)` をちょうど 1 回呼び、論文 upsert と検索履歴記録を行う
  ([`paper-database`](../paper-database/spec.md) 参照)。
- `papers`、`search_query`（人間向けラベル）、`results_csv_path` を
  `st.session_state` に格納する。
- 件数と保存 CSV のファイル名を `st.success` で表示する。

アーカイブファイル名に使う検索ラベルは、`query`, `author`,
`",".join(categories)` のうち最初の非空 SHALL。`query` と `author` が
両方空の場合は [`search-papers`](../search-papers/spec.md) の
Web UI バリデーションで送信が拒否されるため、UI ロジックがここに到達する
ことは無い SHALL。

#### Scenario: Submitting with only categories selected is rejected

- **GIVEN** ユーザーが `cs.AI` と `cs.LG` を選び、`query` と `author` を
  両方空にしたまま、有効な日付を選ぶ
- **WHEN** `Search` をクリック
- **THEN** UI は `st.error` で「query または author のいずれかを指定して
  ください」と表示 SHALL
- **AND** `ArxivClient.search` は **呼ばれない** SHALL
- **AND** `save_papers_to_csv`、`save_search`、DB の upsert もいずれも
  **呼ばれない** SHALL

#### Scenario: A successful search records to the database

- **GIVEN** ユーザーが `query="transformer"`, `categories=["cs.AI"]` を
  入力
- **WHEN** `Search` をクリックし、`ArxivClient.search` が 5 件返す
- **THEN** UI は `save_papers_to_csv` で CSV アーカイブを書く SHALL
- **AND** UI は `st.session_state["db"]` の `save_search("transformer",
  <params dict>, <5 papers>)` をちょうど 1 回呼ぶ SHALL
- **AND** `st.session_state["papers"]` に 5 件が格納される SHALL

#### Scenario: A preset button pre-fills the form

- **GIVEN** ユーザーが `LLM/NLP` プリセットをクリック
- **WHEN** ページが再実行される
- **THEN** `Search query` フィールドに `large language model` が表示 SHALL
- **AND** `Categories` フィールドに `cs.CL`, `cs.AI`, `cs.LG` が表示 SHALL
- **AND** まだ検索は実行されていない SHALL

### Requirement: Results list (rendered on Search, History, and Library pages)

検索フォームの下（History / Library ページでは `Load` クリック後のインライン位置）に、ページは `st.session_state["papers"]` に格納された論文リストを描画 SHALL。そのキーが空なら、検索を促す案内バナーを表示 SHALL。

論文がある場合、ページは以下を描画 SHALL:

- 件数行: `Showing **N** paper(s).`
- ダウンロードボタン群（順番固定）:
  1. `Download CSV` — 現在の `papers` から
     [`export-csv`](../export-csv/spec.md) のインジェクションサニタイズを
     適用してメモリ上で生成。
  2. `Download Excel` — temp ファイル経由で
     [`export-excel`](../export-excel/spec.md) 変換器を呼ぶ。
  3. `Download BibTeX` — メモリ上で
     [`export-citations`](../export-citations/spec.md) の
     `paper_to_bibtex` をループで呼んで `"\n\n"` で結合、
     `arxiv_results.bib` として配信。中間ディスクファイルは作成 SHALL NOT。
  4. `Download RIS` — 同様に `paper_to_ris` を結合、`arxiv_results.ris`
     として配信。
  5. `Download PDFs (ZIP)` — [`download-pdfs`](../download-pdfs/spec.md)
     の `download_papers_pdf` を呼んで `data/pdf/` を共有キャッシュとして
     使い、戻り値のうち `None` でない `Path` を `zipfile.ZipFile` に詰める。
     末尾に `summary.txt`（成功件数 / 失敗件数 / 失敗 arxiv_id）を入れる。
     ボタン押下中は `st.spinner` と推定待ち時間の `st.info` を出す SHALL。
- `published` 日付ごとにグルーピングし、日付降順で表示。各日付グループ内、
  論文ごとに以下を描画 SHALL:
  - タイトル（太字）と、インラインコードバッジとして primary category。
  - 著者（muted キャプション）。
  - アクションボタン: `PDF`（`pdf_url` へリンク）と `arXiv Page`
    （`entry_url` へリンク）。
  - `Tags (comma-separated)` の `st.text_input`。確定時に
    [`tag-management`](../tag-management/spec.md) の `tag_paper` /
    `untag_paper` を差分実行する SHALL。
  - 開閉可能な `Abstract` セクション。abstract に加え、キャプションとして
    `Authors`, `ID`, `Categories` を表示。

#### Scenario: Search page shows BibTeX/RIS/PDF ZIP buttons after a search

- **GIVEN** Search ページが検索成功直後で `st.session_state["papers"]` に
  3 件入っている
- **WHEN** 結果リストが描画される
- **THEN** `Download CSV`, `Download Excel`, `Download BibTeX`,
  `Download RIS`, `Download PDFs (ZIP)` の 5 つのボタンが表示される SHALL
- **AND** ボタン押下のいずれも、押されるまでサーバ側の生成処理を
  発火しない SHALL

#### Scenario: Tag input round-trips to the database

- **GIVEN** ある結果カードの論文 `p` が DB 上タグなしで存在
- **WHEN** ユーザーがカードの `Tags` 入力に `llm, to-read` を入れて確定
- **AND** ページが再実行される
- **THEN** 次回の描画時にも同じカードの `Tags` 入力に `llm, to-read`
  （または DB 順）が表示される SHALL — 入力は `list_papers_by_tag` または
  既存タグ一覧から再構成される

### Requirement: History page

History ページは `data/csv/` にある CSV アーカイブファイル（`results.csv` 以外の `*.csv` すべて）を新しい順に最大 5 件並べる SHALL。
各エントリは以下を表示 SHALL:

- デコード済みクエリラベル（ファイル名 stem から末尾の
  `_YYYYMMDD_HHMMSS` を落とし、`_` をスペースに置換）。
- `YYYY-MM-DD HH:MM` 形式のタイムスタンプ。
- `Load` ボタン。クリックすると、CSV を [`export-csv` のロード関数](../export-csv/spec.md)
  経由で `Paper` レコード列にパースし、`st.session_state["papers"]` を
  埋め、再実行して下に結果リストを描画 SHALL。

アーカイブが無い場合、ページは
`No search history yet. Run a search first.` を表示 SHALL。

### Requirement: Library page

Library ページは DB が持つ完全な履歴と FTS5 を活かす入口 SHALL。
サイドバーのページラジオに 4 つ目の選択肢として `Library` を追加 SHALL。

ページは以下のセクションを上から順に描画 SHALL:

1. **バナー** — `Library uses the local database (data/arxiv_hunt.db).
   The History page shows the last 5 CSV archive files separately.`
   と表示。ユーザーが Library と History の関係を理解できるようにする。
2. **Full-text search** — `Search papers by text` の `st.text_input` 1 つと
   送信ボタン 1 つ。送信時、UI は `db.search_papers(query)` を呼び、
   結果を `st.session_state["papers"]` に格納してから、下に既存の結果
   リスト UI を描画する SHALL。
3. **Browse by tag** — `list_tags(db)` を `st.multiselect` として出す。
   1 つ以上選択された場合、UI は選択された各タグについて
   `list_papers_by_tag(db, name)` を呼び、`arxiv_id` ベースで intersection
   して 1 つの `Paper` リストにまとめ、`st.session_state["papers"]` に
   格納してから結果リストを描画する SHALL。
4. **Search history (DB)** — `db.get_search_history(limit=50)` で取得した
   行を表で並べる SHALL。各行は `searched_at`, `query`, `params`,
   `result_count` を表示し、行ごとに `Load` ボタンを 1 つ持つ。
   `Load` クリック時、UI は `search_results` テーブルから対応する
   `paper_id` 群を rank 順で取得し `Paper` リストを再構成、
   `st.session_state["papers"]` を更新してから結果リストを描画する SHALL。

DB が空の場合、Full-text search セクションは検索結果ゼロ件を、
Browse by tag セクションは「No tags yet.」を、Search history セクションは
「No search history yet.」をそれぞれ表示 SHALL。

#### Scenario: Full-text search renders matching papers

- **GIVEN** DB の `papers` に `title="Attention is All You Need"` の
  論文 1 件が既存
- **WHEN** Library ページの Full-text search に `Attention` と入力して
  送信
- **THEN** UI は `db.search_papers("Attention")` を呼び、戻り値を
  `st.session_state["papers"]` に格納 SHALL
- **AND** 結果リスト UI がその論文を 1 件描画 SHALL

#### Scenario: Browse by tag intersects multiple tags

- **GIVEN** DB に `p1`（タグ `llm`）と `p2`（タグ `llm`, `to-read`）の
  2 件
- **WHEN** ユーザーが `llm` と `to-read` の両方を選択
- **THEN** 結果リストは `p2` のみを描画 SHALL

#### Scenario: Loading a historical search

- **GIVEN** `searches` に 1 行（`id=42`, `query="transformer"`,
  `result_count=5`）と、対応する `search_results` 5 行
- **WHEN** ユーザーがその行の `Load` を押す
- **THEN** UI は `search_results` を rank 順で読んで対応する 5 件の
  `Paper` を `papers` テーブルから取得 SHALL
- **AND** `st.session_state["papers"]` を 5 件で上書き SHALL
- **AND** 下に結果リスト UI を描画 SHALL

### Requirement: Excel Convert page

Excel Convert ページは CSV アップロード、ターゲット言語ドロップダウン（デフォルト `ja`、選択肢: `ja, zh, ko, de, fr, es, pt, ru, ar`）、プライマリボタン `Convert to Excel` を受け付ける SHALL。

クリック時、CSV が添付されていれば、ページは以下を行う SHALL:

- アップロード済みバイト列を一時 CSV ファイルに書く。
- 選択ターゲット言語と `source_lang="en"` で
  [`export-excel`](../export-excel/spec.md) を呼んで一時 `.xlsx` に変換する。
- 変換後のバイト列を `arxiv_results.xlsx` の名前で `Download Excel`
  ボタンとして提供する。
- 変換失敗は `st.error` でインライン表示する。

ボタン押下時にファイルが添付されていなければ、ページは
`Please upload a CSV file first.` を表示 SHALL し、変換器を呼ばない
SHALL NOT。

### Requirement: Launching the UI

ランチャ `run_ui.py` は `python -m streamlit run ui/app.py` をサブプロセスで起動 SHALL し、子プロセスの exit status を伝搬 SHALL。
`ui/app.py` へのパスは `run_ui.py` 自身からの相対で解決 SHALL し、どの作業ディレクトリからでも動作するようにする。

## Implementation pointers

- 入口: `run_ui.py`, `ui/app.py`。
- コンポーネント: `ui/components/sidebar.py`, `ui/components/search_form.py`,
  `ui/components/results_table.py`, `ui/components/history.py`。
- バリデーションと設定: `arxiv_hunt/config.py`。
