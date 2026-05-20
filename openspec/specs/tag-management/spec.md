# tag-management Specification

## Purpose

ユーザー（および他のコード）が短い文字列タグを論文に付与し、タグから
論文を逆引きできるようにする。ストレージは
[`paper-database`](../paper-database/spec.md) の `tag-management` 部に依存する。

## Scope

スコープ内:
- 名前付きタグの冪等作成。
- 論文へのタグ付け／タグ解除。
- 全タグ名の一覧。
- 指定タグを持つ全論文の一覧。
- `arxiv_id` リストへの一括タグ付け。

スコープ外:
- タグのリネーム（現状未サポート）。
- タグの階層／名前空間。
- CLI 入口（現状未配線。Web UI 経由の入口は
  [Requirement: Web UI integration as standard tagging surface](#requirement-web-ui-integration-as-standard-tagging-surface)
  に規定）。

## Requirements

### Requirement: Tag creation is idempotent

`tag_paper(db, arxiv_id, tag_name)` は以下を行う SHALL:

1. タグが存在することを保証し、無ければ作成する（`create_tag` は冪等で、
   既存名なら既存の id を返す）。
2. 論文がデータベース上の `papers` に存在するなら、その論文にタグを
   関連付ける。

同じ引数で `tag_paper` を 2 回呼んだ場合、2 回目は no-op SHALL — 関連付けは
`(paper_id, tag_id)` の主キーで一意化され、`INSERT OR IGNORE` を使う。

#### Scenario: Same tag added twice

- **GIVEN** `arxiv_id="2605.0001"` の論文 `p` が DB に既存
- **AND** タグ `"to-read"` は現状未登録
- **WHEN** `tag_paper(db, "2605.0001", "to-read")` を 2 回呼ぶ
- **THEN** `tags` テーブルは `name="to-read"` の行をちょうど 1 つだけ
  含む SHALL
- **AND** `paper_tags` テーブルもその組に対応する行をちょうど 1 つだけ
  含む SHALL

### Requirement: Untag is forgiving

`untag_paper(db, arxiv_id, tag_name)` は以下を行う SHALL:

- 論文かタグのどちらかが存在しなくても黙って成功 SHALL（例外もエラーも
  返さない）。
- 両方存在するときは `paper_tags` の `(paper_id, tag_id)` 行を削除 SHALL。
- 参照する論文が無くなっても、`tags` 側のタグ定義は残す SHALL
  （孤立タグは許容）。

### Requirement: Bulk tagging

`bulk_tag_papers(db, arxiv_ids, tag_name)` は以下を行う SHALL:

- 引数の id 件数によらずタグを 1 回だけ作成（冪等）。
- `arxiv_ids` 中で既存の論文に入力順でタグを付ける。
- `papers` に存在しない `arxiv_id` は黙ってスキップ。

### Requirement: Listing tags and papers

- `list_tags(db)` は全タグ名を、ケースセンシティブな昇順で返す SHALL。
- `list_papers_by_tag(db, tag_name)` はそのタグを持つ全論文を、
  `papers.id` 昇順（挿入順）で返す SHALL。返却オブジェクトは
  完全に埋まった `Paper` データクラス SHALL。

### Requirement: Tag deletion cascades to associations

`PaperDatabase.delete_tag(name)` 経由でタグを削除すると、それを参照する `paper_tags` 行はすべて削除 SHALL（`ON DELETE CASCADE` で強制）。
対応する `Paper` 行は触らない SHALL NOT。

### Requirement: Web UI integration as standard tagging surface

Streamlit Web UI は本 capability を **標準** のタグ操作入口として露出 SHALL。タグ機能は library 層に閉じない。

UI 側の挙動は以下 SHALL:

- **結果カードからのタグ付け / 解除**: 結果リスト（Search / History /
  Library 各ページが共有する `results_table` コンポーネント）の各論文
  カードに `Tags (comma-separated)` の `st.text_input` を 1 つ置く SHALL。
  入力確定時、UI はカンマ区切りで分割し各要素を `strip()` した集合を作る
  SHALL。

  - 既存集合との差分のうち **新規** 要素は `tag_paper(db, arxiv_id, name)`
    を呼ぶ SHALL。
  - 差分のうち **削除** 要素は `untag_paper(db, arxiv_id, name)` を呼ぶ
    SHALL。
  - どちらも
    [Requirement: Tag creation is idempotent](#requirement-tag-creation-is-idempotent) /
    [Requirement: Untag is forgiving](#requirement-untag-is-forgiving)
    の冪等性に依存しており、重複呼び出しや存在しないタグでも例外を
    上げない SHALL。
- **Library ページの Browse by tag**: `list_tags(db)` の結果を
  `st.multiselect` に並べる SHALL。ユーザーが N 個のタグを選んだ場合、
  UI は各タグについて `list_papers_by_tag(db, name)` を呼び、結果を
  `arxiv_id` ベースで intersection（論理 AND）して 1 つの `Paper`
  リストにまとめる SHALL。
- **タグ名の正規化**: 入力テキストはユーザー入力をそのまま使う SHALL
  — 本変更で `tag-management` の側に新しい正規化ルールは追加 SHALL NOT。
  仕様外の文字種制限を加える場合は別変更とする。

CLI / library 関数のシグネチャは変更 SHALL NOT。

#### Scenario: Adding a tag from a result card

- **GIVEN** 結果カードに `arxiv_id="2605.0001"` の論文が表示されている
- **AND** 現状この論文には DB 上のタグが付いていない
- **WHEN** ユーザーがその論文の `Tags` 入力に `to-read, llm` を入れて確定
- **THEN** UI は `tag_paper(db, "2605.0001", "to-read")` と
  `tag_paper(db, "2605.0001", "llm")` をそれぞれ 1 回ずつ呼ぶ SHALL
- **AND** 同じ入力でもう一度確定しても、追加の API 呼び出しは
  `INSERT OR IGNORE` で no-op となり、`tags` および `paper_tags` の
  行数は変わらない SHALL

#### Scenario: Removing a tag by editing the input

- **GIVEN** 論文 `p` が既に `to-read, llm` の 2 タグを持つ
- **WHEN** ユーザーが `Tags` 入力を `llm` だけに編集して確定
- **THEN** UI は `untag_paper(db, p.arxiv_id, "to-read")` を 1 回呼ぶ
  SHALL
- **AND** `tag_paper` は呼ばれない SHALL（差分なし）
- **AND** `tags` の `to-read` 定義行は残る SHALL（孤立タグ許容）

#### Scenario: Library page intersects multiple tags

- **GIVEN** 論文 `p1` がタグ `llm` を持ち、`p2` がタグ `llm` と `to-read`
  を持つ
- **WHEN** Library ページの Browse by tag で `llm` と `to-read` を両方
  選択
- **THEN** UI は `list_papers_by_tag(db, "llm")` と
  `list_papers_by_tag(db, "to-read")` をそれぞれ 1 回呼ぶ SHALL
- **AND** 結果リストは `p2` のみを表示 SHALL（intersection）

## Implementation status (informational)

`arxiv_hunt/tags.py` は薄いライブラリ層。Streamlit Web UI は結果カードの
`Tags` 入力と Library ページの Browse by tag から本 capability を標準
呼び出し元として使う
（[Requirement: Web UI integration as standard tagging surface](#requirement-web-ui-integration-as-standard-tagging-surface)）。
CLI 入口は依然として未配線。README / Plan で言及されている GitHub-Issue
ベースのタグ運用は本コードベースの機能ではなく、ユーザー向けの
オペレーションメモ。

## Implementation pointers

- `arxiv_hunt/tags.py`
- `arxiv_hunt/database.py` — `PaperDatabase` のタグ関連メソッド。
- Tests: `tests/test_tag_cli.py`（名前に反して、現状 CLI ではなく
  ライブラリ関数を検証している）。
