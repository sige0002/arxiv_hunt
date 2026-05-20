# search-papers Specification

## Purpose

ユーザーから受け取った検索条件（自由文クエリ、著者名、arXiv カテゴリ、
日付範囲）を単一の arXiv API リクエストに変換し、結果を取得して
正規化済みの `Paper` レコード列として返す、統一された arXiv 論文検索
capability を提供する。本 capability は CLI（`scripts/paperhunt_arxiv.py`）、
Streamlit Web UI、スケジュール watcher の 3 か所から再利用される。

## Scope

スコープ内:
- 互いに独立した入力フィールドから arXiv API 検索クエリを組み立てる。
- 明示的な `[start_date, end_date]` ウィンドウ、または「直近 N 日」の
  スライディングウィンドウで結果をフィルタする。
- arXiv API へのリクエストにレート制御をかける。
- すべての入口（CLI 引数パース、Streamlit フォーム投稿）でユーザー入力を
  バリデーションする。

スコープ外:
- 検索結果のディスクや SQLite への永続化（`export-csv` と `paper-database` の責務）。
- 表示用アーティファクトの生成（`export-excel`, `web-ui` の責務）。

## Domain model

`Paper` は本 capability が返す正規化レコード。各 `Paper` は以下の文字列
フィールドを持つ（null は無し。欠損値は空文字列）:

| フィールド | 説明 |
|---|---|
| `arxiv_id` | バージョン接尾辞を含む arXiv の短い識別子（例: `2602.12345v1`）。 |
| `title` | 改行をスペースに畳んだタイトル。 |
| `authors` | 著者表示名を `"; "` で連結したもの。 |
| `abstract` | 改行をスペースに畳んだ要約。 |
| `published` | 投稿日（UTC、`YYYY-MM-DD`）。 |
| `updated` | 最終更新日（UTC、`YYYY-MM-DD`）、または `""`。 |
| `primary_category` | 主カテゴリの arXiv コード。 |
| `categories` | 全カテゴリコードを `"; "` で連結したもの。 |
| `pdf_url` | PDF の絶対 URL、または `""`。 |
| `entry_url` | arXiv abstract ページの絶対 URL。 |

## Requirements

### Requirement: Query composition

本 capability は以下の独立した入力を受け取り、単一の arXiv 検索クエリ文字列に結合 SHALL する:

- `query`（自由文、省略可）
- `author`（省略可）
- `author_operator`（`"AND"` または `"OR"`、デフォルト `"AND"`）
- `category`（単一の arXiv カテゴリコード、省略可）— 後方互換のための入力。
- `categories`（arXiv カテゴリコードのリスト、省略可）— こちらが推奨。

`category` と `categories` の両方が指定された場合は `categories` を優先 SHALL し、
`category` は無視 SHALL される。

`categories`（または `category`）が非空の場合、本 capability はユーザー
部分を括弧で囲み、カテゴリフィルタと `AND` で連結 SHALL:

```
(cat:X OR cat:Y) AND (<user_clause>)
```

`<user_clause>` は `query` と `author` から組み立てる:

- 両方あり: `(<query>) <author_operator> au:"<author>"`。
- `query` のみ: `(<query>)`。
- `author` のみ: `au:"<author>"`。
- **どちらも無し**: user clause は空のまま。本 capability はこの場合でも
  `(cat:X OR …) AND ()` のラッパーをそのまま出してしまう — 後述の
  **Known limitation: empty user clause** を参照。

`author_operator` は `"AND"` または `"OR"` SHALL であること。本 capability は
値を検証せず、それ以外の文字列はそのままクエリに埋め込まれる。呼び出し側は
入口で値を制約 SHALL。

#### Scenario: Query and author combined with AND

- **GIVEN** `query="transformer"`, `author="Yann LeCun"`,
  `author_operator="AND"`, カテゴリ指定なし
- **WHEN** 検索クエリが組み立てられる
- **THEN** 組み立て後のクエリは正確に
  `(transformer) AND au:"Yann LeCun"` となる SHALL

#### Scenario: Categories override single category

- **GIVEN** `category="cs.AI"` と `categories=["cs.CL","cs.LG"]`
- **WHEN** 検索クエリが組み立てられる
- **THEN** カテゴリ節は `cat:cs.CL OR cat:cs.LG` となる SHALL
- **AND** 最終クエリに `cs.AI` は現れない SHALL

### Requirement: Known limitation — empty user clause with categories

`categories` が非空で `query` と `author` がどちらも空のとき、組み立て後のクエリは `(cat:X OR …) AND ()` となる SHALL。
末尾の空括弧は実際の arXiv クエリ構文として無効で、上流の `arxiv` ライブラリはエラーを返すか結果ゼロを返すと考えられる。

入口側はこの状態を入力バリデーションで防ぐ SHALL
（[Requirement: Input validation by entry surface](#requirement-input-validation-by-entry-surface) 参照）。
Web UI は現状この組み合わせを許してしまっており（当該要件の実装メモを参照）、
UI から空結果を引き起こす既知の経路となっている。

ユーザーのクエリ文字列は **そのまま** arXiv に渡され、外側の括弧で
ラップされるだけ。本 capability は arXiv 検索構文をエスケープしない。
呼び出し側は `query` 中で arXiv のフィールド指定子（`ti:`, `abs:`,
`au:`, `cat:`）、ブール演算子、`"phrase"` クォートを使用してよいが、
括弧やクォートの対応は呼び出し側責任。

### Requirement: Date range filter

本 capability は結果を **明示ウィンドウ** か **スライディングウィンドウ** のいずれかでフィルタ SHALL（両方同時は不可）:

- `start_date` **または** `end_date` が指定された場合はそちらを使用 SHALL し、
  `days` は無視 SHALL する。`start_date` はその日の `00:00:00 UTC` から
  inclusive、`end_date` はその日の `23:59:59 UTC` まで inclusive。
- それ以外で `days` が `None` でない値で指定された場合、`days` 日以内
  （UTC の "now" 基準）に publish された論文のみを返す SHALL。本 capability
  自身は `days >= 1` を要求しないため、入口側で非正の値を弾く SHALL。
- どちらも指定されなければ、日付フィルタは適用しない。

#### Scenario: Explicit window beats `days`

- **GIVEN** `days=7`, `start_date=2026-05-01`, `end_date=2026-05-10`
- **WHEN** 検索が実行される
- **THEN** `published` が `2026-05-01T00:00:00Z` から
  `2026-05-10T23:59:59Z` の範囲の論文のみ返す SHALL

#### Scenario: Sliding window via `days`

- **GIVEN** `days=14`、`start_date`/`end_date` なし、現在時刻 `2026-05-20T12:00:00Z`
- **WHEN** 検索が実行される
- **THEN** `published >= 2026-05-06T12:00:00Z` の論文のみ返す SHALL

### Requirement: Result ordering and limits

結果は arXiv API に対し投稿日の降順でリクエスト SHALL する。返却リストも
それに合わせて並べる SHALL — 最新投稿が先頭。

本 capability は `max_results` を直接 `arxiv.Search` に渡す（arXiv が
最大その件数までの候補を返す）SHALL し、その後日付フィルタを適用 SHALL し、
最後に通過した論文を API 順序のまま返す SHALL。結果として:

- 返却リストの件数は **最大** `max_results` 件である SHALL。
- 返却リストは、呼び出し側の日付ウィンドウが許容する件数より **少なく** なる
  ことが MAY ある: 上位 `max_results` 件の候補のうち一部がウィンドウ外にあれば
  落とされ、ウィンドウ内に **入る** より古い候補をバックフィルしに行く
  ことは **無い**。完全な日付ウィンドウが必要な呼び出し側は `max_results`
  を相応に上げる SHALL。

`max_results` のデフォルトは `10`。定数 `MAX_RESULTS_LIMIT`（`200`）は
UI 側の上限であり、本 capability 自体は強制しない。

### Requirement: Rate limiting and API politeness

arXiv API 呼び出しはすべて `arxiv.Client` を介して `delay_seconds = ARXIV_RATE_LIMIT_SECONDS`（デフォルト `3.0` 秒）で行う SHALL。
連続するページ取得が arXiv のポライトネスガイドラインを守るため。API キーは不要かつ未使用。

### Requirement: Input validation by entry surface

入口（CLI と Streamlit フォーム）は `ArxivClient.search` を呼ぶ前に入力をバリデート SHALL。
この 2 つの入口は **異なる** ルールセットを適用しており、両方をここに列挙する。`ArxivClient` 自体は入力バリデーションを **行わない** ため、すべての値はそのまま arXiv に届く。

両入口共通（`config.SHELL_META_CHARS` で定義されるセット）:

- **長さ上限**: `query` と `author` はそれぞれ最大
  `MAX_QUERY_LENGTH`（`500`）文字 SHALL。
- **シェルメタ文字の拒否**: `;`, `|`, `&`, `` ` ``, `$` のいずれかが
  `query` または `author` に現れたら、API 呼び出し前にユーザー可視の
  エラーで拒否 SHALL。

CLI 専用（`scripts/paperhunt_arxiv.py`）:

- **`--query` は必須** で、`strip()` 後に非空 SHALL。したがって CLI からは
  著者のみ・カテゴリのみの検索は現状不可。
- **`--days >= 1`** を強制 SHALL。
- **`--max >= 1`** を強制 SHALL。上限 `MAX_RESULTS_LIMIT`（`200`）は
  CLI では **強制しない**。

Web UI 専用（`ui/components/search_form.py`）:

- **非空ユーザー句**: `query.strip()` または `author.strip()` の少なくとも
  一方が非空 SHALL。`categories` だけが指定され、`query` と `author` が
  両方空の場合は拒否 SHALL — これは
  [Requirement: Known limitation — empty user clause with categories](#requirement-known-limitation--empty-user-clause-with-categories)
  で指摘された `(cat:X OR …) AND ()` 経路を UI 入口で塞ぐためである。
- **日付整合**: `start_date` は `end_date` 以前である SHALL。
- **数値範囲**: `max_results` は `[1, MAX_RESULTS_LIMIT]` の範囲 SHALL
  （`st.number_input(min_value=1, max_value=200)` で強制）。フォームは
  `days` を露出しない。

バリデーション失敗時、CLI は非ゼロステータスでログ出力して終了 SHALL し、
Web UI はインラインでエラーを表示し、検索を実行しない SHALL。

#### Scenario: Reject shell metacharacters

- **GIVEN** `query="machine learning; rm -rf /"` を CLI 経由で投入
- **WHEN** CLI が引数をパースする
- **THEN** CLI は禁止文字をログに出し、arXiv API を呼ばずに非ゼロで
  終了 SHALL

#### Scenario: CLI rejects an empty query even when category is supplied

- **GIVEN** CLI を `--category cs.AI` のみ（`--query` なし）で呼び出す
- **WHEN** `argparse` が引数をパースする
- **THEN** `--query` が `required=True` のため CLI は非ゼロで終了 SHALL
- **AND** arXiv API 呼び出しは行われない SHALL

#### Scenario: Web UI rejects categories-only submission

- **GIVEN** Web UI のフォームで `query` と `author` を両方空のまま、
  `categories=["cs.AI", "cs.LG"]` を選択
- **WHEN** ユーザーが `Search` を押す
- **THEN** UI は「query または author のいずれかを指定してください」と
  インラインで `st.error` を表示 SHALL
- **AND** `ArxivClient.search` は **呼ばれない** SHALL
- **AND** `(cat:cs.AI OR cat:cs.LG) AND ()` という空ユーザー句クエリは
  arXiv に送られない SHALL

#### Scenario: Web UI accepts author-only submission

- **GIVEN** Web UI のフォームで `query` を空、`author="Yann LeCun"` を入力、
  `categories=["cs.LG"]` を選択
- **WHEN** ユーザーが `Search` を押す
- **THEN** バリデーションは通過 SHALL
- **AND** `ArxivClient.search` が呼ばれ、組み立てクエリは
  `(cat:cs.LG) AND (au:"Yann LeCun")` となる SHALL

### Requirement: Normalization of returned papers

arXiv API が返す各結果に対し、本 capability は以下を行って `Paper` レコードを生成 SHALL:

- `title` と `abstract` 中のすべての `\n` を 1 個のスペースに置換し、
  前後の空白を削除する。
- `authors` を `"; "` で、`categories` を `"; "` で連結する。
- `published` と `updated` を UTC の `YYYY-MM-DD` 形式に整形する。
- 欠損する任意フィールド（`pdf_url`, `updated`）は `""` で埋める。

## Implementation pointers

- `arxiv_hunt/client.py::ArxivClient.search`
- `arxiv_hunt/models.py::Paper.from_arxiv_result`
- `arxiv_hunt/config.py` — `MAX_QUERY_LENGTH`, `MAX_RESULTS_LIMIT`,
  `SHELL_META_CHARS`, `ARXIV_RATE_LIMIT_SECONDS`。
- CLI 入口: `scripts/paperhunt_arxiv.py`
- UI 入口: `ui/components/search_form.py`
