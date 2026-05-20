# export-excel Specification

## Purpose

検索結果 CSV を人間レビュー＆翻訳しやすい Excel ワークブックに変換する。
各 abstract セルは、`TRANSLATE` 数式が入った連れのカラムにミラーリングされ、
ワークブックは固定ヘッダ、最上行フリーズ、オートフィルタ、広げたカラム幅で
装飾される。

## Scope

スコープ内:
- `export-csv` が生成した CSV を読み、シート 1 枚の `.xlsx` を出力する。
- 呼び出し側が指定したソース／ターゲット言語を埋め込んだ
  `_xlfn.TRANSLATE` 数式を、各行の abstract セル参照で生成する。
- 計算出力カラム 2 つを追加する: `abstract_translated`（数式）と
  `relevance_score`（手入力用に空欄）。
- CLI 呼び出し（`scripts/csv_to_excel_translate.py`）。
- Web UI 呼び出し（検索結果ダウンロード、Excel Convert ページ）。

スコープ外:
- 翻訳そのものの実行（Excel/Google Sheets が表示時に数式を評価する）。
- 注釈や relevance_score を CSV/SQLite に書き戻すこと。

## Output layout

生成されるワークシートは `Papers` と命名される。カラムは順に:

1. `arxiv_id`
2. `title`
3. `authors`
4. `published`
5. `updated`
6. `primary_category`
7. `categories`
8. `pdf_url`
9. `entry_url`
10. `abstract`
11. `abstract_translated`  ← 数式
12. `relevance_score`      ← 意図的に空欄

## Requirements

### Requirement: Header row styling

行 1 は上記レイアウトのカラム名を含む SHALL、以下の体裁で:

- フォントは白の太字 11pt。
- 背景は `#B31B1B`（arXiv クリムゾン）の単色塗りつぶし。
- 水平・垂直の中央揃え、折り返し有効。

### Requirement: TRANSLATE formula per row

各データ行 `r`（`r >= 2`）の `abstract_translated` セルは以下の形式の数式 SHALL を含む:

```
=_xlfn.TRANSLATE(<abstract-cell-ref>,"<source_lang>","<target_lang>")
```

ここで `<abstract-cell-ref>` は行 `r` の `abstract` セルの A1 形式アドレス。
正規のカラム順では `abstract` は **10 番目** のカラム（`J`）、
`abstract_translated` は **11 番目**（`K`）。

言語コードはデフォルトで `"en"`（source）と `"ja"`（target）SHALL とし、
呼び出し側が変更可能 SHALL。値は数式文字列に **そのまま** 埋め込まれる —
変換器は二重引用符などの特殊文字をエスケープしない。呼び出し側は短い
ISO 639-1 コード（`"en"`, `"ja"`, `"de"` など）を渡す SHALL し、任意文字列を
使うべきでない (SHOULD NOT)。

`relevance_score` セルは空のまま SHALL。

#### Scenario: Default language pair

- **GIVEN** 論文 3 件を持つ CSV と、`--source-lang`/`--target-lang` の
  上書きなし
- **WHEN** CLI が変換する
- **THEN** 2 行目の K 列は `=_xlfn.TRANSLATE(J2,"en","ja")` を含む SHALL
- **AND** 3, 4 行目もそれぞれ `J3`, `J4` を参照する類似の数式を含む SHALL

#### Scenario: Empty input produces a header-only workbook

- **GIVEN** ヘッダ行のみの CSV
- **WHEN** 変換器が動く
- **THEN** 生成されるワークブックは装飾済みヘッダ 1 行を含み、データ行は
  含まない SHALL
- **AND** オートフィルタ範囲は少なくとも 1〜2 行を覆う SHALL
  （Excel は 1 行のみの範囲にオートフィルタを適用できないため）

### Requirement: Worksheet ergonomics

ワークシートは以下の体裁で生成 SHALL:

- 1 行目フリーズ（`freeze_panes = "A2"`）。
- 全データ範囲を覆うオートフィルタ。
- 事前定義マップに基づくカラム幅（例: `title=50`, `abstract=60`、
  デフォルト `15`）。
- すべての `abstract` セルと `abstract_translated` セルで折り返し有効。

### Requirement: Default paths

呼び出し側が `csv_path` または `output_path` を省略した場合、以下のデフォルトを適用 SHALL:

- `csv_path` のデフォルトは `data/csv/results.csv`。
- `output_path` のデフォルトは `data/excel/<csv-stem>.xlsx`。出力ディレクトリが無ければ作成 SHALL。

### Requirement: Input validation (CLI)

CLI は入力 CSV パスが存在しない／通常ファイルでない場合に非ゼロステータスとログ出力で失敗 SHALL。
その場合変換は試みない SHALL。

## Implementation pointers

- `arxiv_hunt/excel_converter.py::convert_csv_to_excel`
- `arxiv_hunt/config.py::EXCEL_EXTRA_COLUMNS`
- CLI: `scripts/csv_to_excel_translate.py`
- UI: `ui/components/results_table.py::_generate_excel_bytes`、および
  `ui/app.py` 内の Excel Convert ページ。
