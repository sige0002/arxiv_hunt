# arxiv_hunt — Capability 仕様書

このディレクトリは、現在の `arxiv_hunt` が何を行うかを capability 単位で
ドキュメント化したもの。各サブディレクトリには `spec.md` が 1 つあり、
その capability の目的・スコープ・要件を具体的な受け入れシナリオとともに記述する。

## Capability マップ

```
ユーザー向けインタフェース        Capability                          ストレージ
──────────────────────       ──────────────────────         ───────────
CLI
  paperhunt_arxiv ─────▶ search-papers ─────────────────┐
                                  │                     │
  csv_to_excel_translate          ▼                     │
                         export-csv  ──┐                │
                                       ▼                ▼
Streamlit UI ──────────▶ export-excel ─┴──▶ data/csv data/excel
  Search ページ
  History ページ
  Excel Convert ページ          ─▶ export-citations (ライブラリのみ)
                                ─▶ download-pdfs     (ライブラリのみ)

(現状の呼び出し元なし) ─▶ paper-database ◀──▶ tag-management
(現状の呼び出し元なし) ─▶ scheduled-watch ──▶ Slack メッセージ文字列
                                              (HTTP 送信は未実装)
```

## Specs

| Capability | 内容 |
|---|---|
| [search-papers](search-papers/spec.md) | クエリ合成、日付/カテゴリ/著者フィルタ、レート制御、入力バリデーション |
| [export-csv](export-csv/spec.md) | 二重書き込み（latest + アーカイブ）、CSV インジェクション対策、アーカイブ世代管理 |
| [export-excel](export-excel/spec.md) | CSV → `.xlsx` を `_xlfn.TRANSLATE` 式とシート装飾付きで生成 |
| [export-citations](export-citations/spec.md) | BibTeX `@article{…}` および RIS 形式の出力 *(ライブラリのみ — 呼び出し元なし)* |
| [download-pdfs](download-pdfs/spec.md) | 論文単位の PDF ダウンロードと決定論的ファイル名・レート制御 *(ライブラリのみ)* |
| [paper-database](paper-database/spec.md) | SQLite スキーマ、FTS5 ミラー、`arxiv_id` キーの upsert、検索履歴 *(ライブラリのみ)* |
| [tag-management](tag-management/spec.md) | 論文へのタグ CRUD、一括タグ付け *(ライブラリのみ)* |
| [scheduled-watch](scheduled-watch/spec.md) | YAML 駆動の一括検索 + Slack 風メッセージ整形 *(HTTP POST は未実装)* |
| [web-ui](web-ui/spec.md) | Streamlit の Search / History / Excel Convert ページ |

## 実装ステータスの凡例

一部の capability はライブラリ層としてのみ存在する — 完全に実装され
ユニットテストもあるが、現状ではどの CLI コマンドや UI ページからも
呼ばれていない。該当する spec では `## Implementation status` セクションで
それを明示し、「README が触れている内容」と「実際にエンドツーエンドで
配線されている内容」のギャップを隠さず記録している。

## 本ディレクトリで用いる規約

- 規範動詞は **SHALL** のみ（RFC 2119 の "MUST" に相当）。要件本文では
  "should" / "may" は使わず、柔軟性は周辺の散文側に寄せる。
- 各 `### Requirement: …` ブロックには 0 個以上の `#### Scenario: …` が続く。
  シナリオは Given/When/Then を箇条書きで書き、テスト可能な形にする。
- spec 間の相互参照は相手側 capability の `spec.md` へのリンクで行う
  （例: `[`export-csv`](../export-csv/spec.md)`）。
- 各 spec 末尾の Implementation pointers は要件を満たすモジュール／テストを
  列挙する — レビュー時や将来の安全な削除確認に有用。
