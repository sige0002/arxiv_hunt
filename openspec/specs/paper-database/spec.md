# paper-database Specification

## Purpose

arXiv 論文、検索履歴、論文ごとのタグを 1 つのローカル SQLite データベースに
永続化する。タイトルと abstract に対する全文検索（FTS5）も提供する。
タグ付け、将来の watcher 履歴、将来の UI 検索など、他 capability が
読み込み元として使う長期ストアとして機能する。

## Scope

スコープ内:
- スキーマ作成、接続時マイグレーション、既存テーブル時は no-op。
- `arxiv_id` をキーとした `Paper` レコードの冪等 upsert。
- タイトルと abstract への全文検索。
- 検索クエリ、そのパラメータ、マッチした論文を記録する。
- タグ定義と、論文＝タグの多対多関連（API 表層は `tag-management`、
  ストレージは本仕様）。

スコープ外:
- ネットワーク I/O や外部サービス。
- CLI 入口（現状未配線。Web UI 経由の入口は
  [Requirement: Web UI integration as standard reader/writer](#requirement-web-ui-integration-as-standard-readerwriter)
  に規定）。

## Storage

データベースファイルはデフォルトで `data/arxiv_hunt.db` SHALL。呼び出し
側はパスを上書き可能 MAY。親ディレクトリが無ければ作成 SHALL。

SQLite 接続は以下を満たす SHALL:

- `journal_mode = WAL` を設定（並行読み取り挙動が向上）。
- `foreign_keys = ON` を設定（削除のカスケードを有効化）。
- `row_factory` に `sqlite3.Row` を使う。

## Schema

本 capability は接続オープン時に以下のテーブルを冪等に作成 SHALL:

```text
papers
  id           INTEGER PK AUTOINCREMENT
  arxiv_id     TEXT NOT NULL UNIQUE
  title        TEXT NOT NULL
  authors      TEXT NOT NULL
  abstract     TEXT NOT NULL DEFAULT ''
  published    TEXT NOT NULL DEFAULT ''
  updated      TEXT NOT NULL DEFAULT ''
  primary_category TEXT NOT NULL DEFAULT ''
  categories   TEXT NOT NULL DEFAULT ''
  pdf_url      TEXT NOT NULL DEFAULT ''
  entry_url    TEXT NOT NULL DEFAULT ''
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))

searches
  id            INTEGER PK AUTOINCREMENT
  query         TEXT NOT NULL
  params        TEXT NOT NULL DEFAULT '{}'   -- JSON-encoded
  result_count  INTEGER NOT NULL DEFAULT 0
  searched_at   TEXT NOT NULL DEFAULT (datetime('now'))

search_results
  search_id INTEGER NOT NULL REFERENCES searches(id) ON DELETE CASCADE
  paper_id  INTEGER NOT NULL REFERENCES papers(id)   ON DELETE CASCADE
  rank      INTEGER NOT NULL DEFAULT 0
  PRIMARY KEY (search_id, paper_id)

tags
  id   INTEGER PK AUTOINCREMENT
  name TEXT NOT NULL UNIQUE

paper_tags
  paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE
  tag_id   INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE
  PRIMARY KEY (paper_id, tag_id)

papers_fts  (virtual table, FTS5)
  title    -- papers からミラー
  abstract -- papers からミラー
  content=papers, content_rowid=id
```

## Requirements

### Requirement: FTS5 mirror maintained by triggers

`papers_fts` は 3 つのトリガによって `papers` と同期 SHALL:

- `papers_ai` — insert 時、`papers_fts` に insert。
- `papers_ad` — delete 時、`papers_fts` に `'delete'` 行を書く。
- `papers_au` — update 時、`papers_fts` に `'delete'` 続けて `'insert'` を書く。

`papers` への `INSERT`, `UPDATE`, `DELETE` の後、新しい title/abstract に
対する FTS5 マッチは新しい状態を反映する SHALL。

#### Scenario: Updating a title is searchable

- **GIVEN** `title="Old title"` で論文を挿入
- **WHEN** 同じ論文を `title="New title"` で再度 upsert
- **AND** `search_papers("New")` を呼ぶ
- **THEN** その論文が返る SHALL
- **AND** `search_papers("Old")` は 0 行を返す SHALL

### Requirement: Upsert is keyed by arxiv_id

`upsert_paper` は以下のように振る舞う SHALL:

- 指定 `arxiv_id` の行が既存なら、可変フィールドすべて
  （title, authors, abstract, published, updated, primary_category,
   categories, pdf_url, entry_url）を新しい値で上書き SHALL。
  `created_at` と代理キー `id` は変えない SHALL NOT。
- 行が無ければ新規 insert SHALL。

関数はどちらの場合でも行の `id` を返す SHALL。

upsert 全体での `arxiv_id` の一意性はカラムの `UNIQUE` 制約で保証 SHALL。

### Requirement: Full-text search via FTS5

`search_papers(query)` は `papers_fts` に対する FTS5 `MATCH` クエリを実行 SHALL し、マッチした `Paper` 行を FTS5 `rank` 順（マッチが良い順）で返す SHALL。

本 capability は呼び出し側のクエリ文字列を **そのまま** FTS5 に渡す —
FTS5 構文をエスケープしないので、呼び出し側は FTS5 演算子
（`AND`, `OR`, `NEAR`, `"phrase"` 等）を使ってよい MAY が、信頼できない
入力のエスケープは呼び出し側責任 SHALL。

### Requirement: Search history records its inputs

`save_search(query, params, papers)` は以下を行う SHALL:

1. `papers` の各 `Paper` を upsert し、同順で DB id を集める。
2. `searches` に 1 行 insert する。`params` は JSON エンコード、
   `result_count = len(papers)`。
3. 各論文ごとに `search_results` へ 1 行 insert する。`rank` は入力リスト
   での 0 始まりインデックス。

関数は新しい search id を返す SHALL。

トランザクション挙動は現在の `sqlite3` 接続モードに従う: 書き込みは
`with self.conn:` ブロック越しに行うため、トップレベルの `save_search`
呼び出しは成功時にコミット、例外時にロールバックする。外側の
`with self.conn:` の内側からネストして呼ぶと、その外側トランザクションを
共有することになる。本 capability はこのケースの挙動を文書化も保証も
しないため、呼び出し側はそれに依存 SHALL NOT。

`get_search_history(limit)` は直近 `limit` 件（デフォルト `50`）の検索を
新しい順の dict リストとして返す SHALL。`params` は Python dict に
デコードして返す。

### Requirement: Cascade on delete

`papers` から行を削除すると、以下も削除 SHALL:

- `search_results` の対応行。
- `paper_tags` の対応行。
- FTS5 ミラー（`papers_ad` トリガ経由）。

`searches` の行を削除するとその `search_results` にカスケード SHALL。

`tags` の行を削除するとその `paper_tags` にカスケード SHALL。

検索やタグの削除によって `papers` 行そのものは削除されない SHALL NOT —
論文はどちらより長く生きる。

### Requirement: Web UI integration as standard reader/writer

Streamlit Web UI は本 capability を **標準** の永続化レイヤとして利用 SHALL。
セッションごとに `PaperDatabase(<default path>)` を 1 つ生成し
`st.session_state["db"]` に保持 SHALL。デフォルトパスは
[Storage](#storage) に従い `data/arxiv_hunt.db`。
他 capability（[`export-csv`](../export-csv/spec.md) のアーカイブ）は
副次的なバックアップとして残ってよい MAY。

UI 側の書き込み・読み取りは以下 SHALL:

- **検索成功時に upsert + 履歴記録**: Search ページが `ArxivClient.search`
  から非空の結果を受け取ったら、`save_search(query=<人間向けラベル>,
  params=<検索フォーム入力をシリアライズした dict>, papers=<結果>)` を
  ちょうど 1 回呼び出す SHALL。これにより
  [Requirement: Search history records its inputs](#requirement-search-history-records-its-inputs)
  に従って全論文が upsert され、`searches` 行と `search_results` 行が
  挿入される。
- **タグ入力**: 結果リストの各カードに `Tags (comma-separated)` の
  `st.text_input` を 1 つ置き、差分を
  [`tag-management`](../tag-management/spec.md) 経由で `tag_paper` /
  `untag_paper` に流す SHALL。
- **Library ページの全文検索**: `Library` ページの `Full-text search`
  セクションが入力テキストを `db.search_papers(query)` にそのまま渡す
  SHALL。FTS5 構文は呼び出し側責任のまま
  （[Requirement: Full-text search via FTS5](#requirement-full-text-search-via-fts5)）。
- **Library ページのタグ絞り込み**: 選択された全タグそれぞれに対し
  `list_papers_by_tag` を呼び、結果を `arxiv_id` で intersection
  （論理 AND）して 1 つの `Paper` リストにまとめ、既存の結果リスト UI で
  描画 SHALL。
- **Library ページの履歴閲覧**: `db.get_search_history(limit=50)` の各行を
  リスト表示し、各行の `Load` ボタンが `search_results` から `Paper` を
  再構成して `st.session_state["papers"]` を更新 SHALL。

スキーマや既存メソッドのシグネチャは変更 SHALL NOT — 本要件は
**UI 配線の追加のみ** を規定する。

#### Scenario: A successful search persists to the database

- **GIVEN** Web UI の Search フォームを `query="transformer"`,
  `max_results=5` で送信し、`ArxivClient.search` が 5 件の `Paper` を
  返す
- **WHEN** Search ページが結果を受け取る
- **THEN** `papers` テーブルに 5 件が upsert される SHALL
- **AND** `searches` テーブルに 1 行追加され、`query` 列は人間向けラベル
  （例 `"transformer"`）を、`params` 列はフォーム入力の JSON 表現を、
  `result_count` 列は `5` を持つ SHALL
- **AND** `search_results` テーブルにその検索 id と 5 つの paper id を
  紐づける行が 5 つ追加される SHALL

#### Scenario: Library page renders FTS5 hits

- **GIVEN** `papers` テーブルに既に
  `title="Attention is All You Need"` の論文が 1 件存在
- **WHEN** Library ページの Full-text search に `Attention` を入力して
  送信
- **THEN** UI は `db.search_papers("Attention")` を呼ぶ SHALL
- **AND** 戻り値の `Paper` リストを既存の結果リスト UI に渡し、その論文を
  描画 SHALL

## Implementation status (informational)

スキーマと CRUD メソッドは実装済みかつユニットテストもある。Streamlit UI
は本 capability を標準の永続化レイヤとして読み書きする
（[Requirement: Web UI integration as standard reader/writer](#requirement-web-ui-integration-as-standard-readerwriter)）。
CSV アーカイブによる履歴（[`export-csv`](../export-csv/spec.md) と
[`web-ui`](../web-ui/spec.md) の History ページ）は併存するバックアップ。

## Implementation pointers

- `arxiv_hunt/database.py::PaperDatabase`
- Tests: `tests/test_database.py`
