# export-csv Specification

## Purpose

`Paper` レコード列を、表計算アプリで安全に開ける形式かつ直近検索の
ローリングアーカイブを残す形式で CSV に永続化する。CLI が検索のたびに
利用し、Web UI もユーザーが検索フォームを送信したときに利用する。

## Scope

スコープ内:
- 検索 1 回につき CSV を 2 ファイル書き出す: 固定名の「最新結果」
  ファイルと、タイムスタンプ付きアーカイブコピー。
- アーカイブを一定世代数に枝刈りする。
- CSV / スプレッドシートの数式インジェクションを防ぐ。
- アーカイブ CSV を `Paper` レコード列に読み戻す。

スコープ外:
- 数式付き Excel 出力（`export-excel` の責務）。
- SQLite への永続化（`paper-database` の責務）。

## Domain rules

- 正規の CSV カラム順は:
  `arxiv_id, title, authors, published, updated, primary_category,
   categories, pdf_url, entry_url, abstract`。
- 最新結果ファイル名は固定で `results.csv`。
- アーカイブファイル名のパターンは
  `{sanitized-query}_{YYYYMMDD_HHMMSS}.csv`。タイムスタンプはローカルの
  壁時計時刻、`{sanitized-query}` は検索ラベルを `sanitize_filename` に
  通したもの。

## Requirements

### Requirement: Dual write on every save

1 回の保存で出力ディレクトリ（デフォルト `data/csv/`）に 2 ファイル出力 SHALL:

1. `results.csv` — 保存ごとに最新結果で上書き。
2. `<sanitized-query>_<timestamp>.csv` — 新しいアーカイブコピー。

両ファイルは同一内容かつ **Domain rules** で定義したカラム順で書き出す
SHALL し、UTF-8 エンコード、`\n` 行終端で書く SHALL。

#### Scenario: A new search overwrites results.csv but adds a new archive

- **GIVEN** `data/csv/results.csv` が以前の検索によって既に存在する
- **WHEN** `2026-05-20 12:00:00` にクエリ `"diffusion models"` で 7 件を
  保存する
- **THEN** `data/csv/results.csv` はちょうどその 7 行を含む SHALL
- **AND** `data/csv/diffusion_models_20260520_120000.csv` も同一内容で
  存在する SHALL

### Requirement: CSV-injection sanitization

`sanitize_cells` が真（デフォルト）の場合、本 capability はセル値の先頭文字が `=`, `+`, `-`, `@` のいずれかなら ASCII シングルクォート `'` を 1 つ prefix する SHALL。
書き出し前に全行・全カラムへ適用 SHALL。

アーカイブを読み戻すときは、先頭の `'` を、その直後の文字が
`=`, `+`, `-`, `@` のいずれかである場合に **限って** 取り除き、元の値を
復元 SHALL。

#### Scenario: Title beginning with `-` is escaped

- **GIVEN** `title="-Net: a new architecture"` を持つ `Paper`
- **WHEN** `save_papers_to_csv` をサニタイズ有効で呼び出す
- **THEN** 書き出された CSV のタイトルセルは `'-Net: a new architecture`
  になる SHALL

#### Scenario: Round-trip via load_papers_from_csv

- **GIVEN** `Paper` リストのうち、1 件は `title="-Net: a new architecture"`、
  1 件は `abstract="@(deprecated) method"` を持つ
- **WHEN** `save_papers_to_csv(..., sanitize_cells=True)` で書き出し、
  得られたアーカイブを `load_papers_from_csv` で読み戻す
- **THEN** 読み戻したリストは元のリストとフィールド単位で一致 SHALL —
  書き込み時に挿入された先頭 `'` は読み込み時に除去 SHALL される。

### Requirement: Filename sanitization

アーカイブファイル名のクエリ部分は、以下の順で適用するサニタイズに通す SHALL:

- リテラル部分文字列 `..` を除去（パストラバーサル対策）。
- `/`, `\`, ASCII NUL（`\x00`）を `_` に置換。
- Python 正規表現 `[\w\-.]` にマッチしない残りの文字を `_` に置換。
  `\w` はデフォルトで **Unicode 対応** のため、非ラテン文字の文字種は
  そのまま保持される。
- 連続する `_` を 1 個に縮約。
- 先頭と末尾の `_` および `.` を除去。
- 最大 200 文字に切り詰め。
- 何も残らなければリテラル `"unnamed"` にフォールバック。

### Requirement: Archive retention

本 capability はクリーンアップルーチンを提供 SHALL:

- 出力ディレクトリ内の `results.csv` を **除く** すべての `*.csv` を列挙する。
  マッチは拡張子ベース — アーカイブファイル名パターンに合致しなくても
  削除対象になる。したがって呼び出し側は設定された出力ディレクトリを
  arxiv_hunt 専有として扱う SHALL。
- 更新時刻の新しい順にソートする。
- `keep` 件（デフォルト `MAX_ARCHIVES = 5`）を超える分を削除する。

`results.csv` はクリーンアップで触れない SHALL。

Web UI は保存成功のたびにクリーンアップを呼ぶ SHALL が、CLI は現状呼ばない
ため、CLI の `data/csv/` は Web UI を起動するかユーザーが手で消すまで
無制限に増える。

#### Scenario: Cleanup with 7 archives keeps the 5 newest

- **GIVEN** 出力ディレクトリに `results.csv` と、それぞれ異なる mtime を
  持つアーカイブ CSV が 7 個ある
- **WHEN** `cleanup_old_archives(keep=5)` を実行
- **THEN** 最も新しい 5 個のアーカイブと `results.csv` が残る SHALL
- **AND** 古い 2 個のアーカイブは削除 SHALL

### Requirement: Output-directory creation

設定された出力ディレクトリが存在しない場合、本 capability は書き込み前に（親ディレクトリ含めて）作成 SHALL。

## Implementation pointers

- `arxiv_hunt/csv_io.py` — `save_papers_to_csv`, `load_papers_from_csv`,
  `list_recent_archives`, `cleanup_old_archives`, `sanitize_filename`,
  `_sanitize_cell`, `_CSV_INJECTION_PREFIXES`。
- `arxiv_hunt/config.py` — `CSV_COLUMNS`, `CSV_OUTPUT_DIR`,
  `RESULTS_CSV_FILENAME`。
