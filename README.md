# arxiv_hunt

arXiv 論文の検索・CSV/Excel エクスポート・PDF ダウンロード・タグ管理を行うツール。CLI と Streamlit Web UI の両方に対応。

## 必要環境

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャ)

arXiv API は API キー不要で利用できます。

## セットアップ

```bash
# リポジトリに移動
cd arxiv_hunt

# 依存パッケージのインストール
uv sync

# Web UI も使う場合
uv sync --extra ui

# 開発用ツール (pytest, mypy) も入れる場合
uv sync --extra dev
```

### 環境変数 (任意)

```bash
cp .env.example .env
```

`.env` で以下を設定できます:

| 変数名 | デフォルト | 説明 |
|---|---|---|
| `ARXIV_DEFAULT_DAYS` | `7` | 検索対象の日数 |
| `ARXIV_DEFAULT_MAX_RESULTS` | `10` | 最大取得件数 |
| `ARXIV_RATE_LIMIT` | `3.0` | API リクエスト間隔 (秒) |
| `CSV_OUTPUT_DIR` | `data/csv` | CSV 出力先 |
| `EXCEL_OUTPUT_DIR` | `data/excel` | Excel 出力先 |

## 使い方

### CLI で論文検索

```bash
uv run python scripts/paperhunt_arxiv.py \
  --query "large language model" \
  --days 14 \
  --max 50 \
  --category cs.CL \
  -v
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `--query` | Yes | 検索クエリ (最大500文字) |
| `--days` | No | 過去何日分を検索 (デフォルト: 7) |
| `--max` | No | 最大取得件数 (デフォルト: 10, 上限: 200) |
| `--category` | No | arXiv カテゴリで絞り込み (例: `cs.AI`, `cs.CL`) |
| `-v` / `--verbose` | No | デバッグログを表示 |

結果は `data/csv/results.csv` に保存され、タイムスタンプ付きアーカイブも自動作成されます (最大5世代保持)。

### CSV → Excel 変換

検索結果の CSV を、翻訳用の TRANSLATE 関数付き Excel に変換します。

```bash
uv run python scripts/csv_to_excel_translate.py \
  --input data/csv/results.csv \
  --output results.xlsx \
  --source-lang en \
  --target-lang ja
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `--input` | No | 入力 CSV パス (デフォルト: `data/csv/results.csv`) |
| `--output` | No | 出力 Excel パス (未指定時は自動生成) |
| `--source-lang` | No | 翻訳元言語 (デフォルト: `en`) |
| `--target-lang` | No | 翻訳先言語 (デフォルト: `ja`) |

### Web UI (Streamlit)

```bash
uv run python run_ui.py
```

ブラウザで `http://localhost:8501` にアクセスすると以下の機能が使えます:

- 検索フォーム (カテゴリ選択、日付範囲指定、著者フィルタ)
- 検索結果の表示・CSV/Excel ダウンロード
- 検索履歴の閲覧・再実行
- CSV → Excel 変換

### Make コマンド

```bash
make install                          # 依存パッケージのインストール
make search QUERY="transformer" DAYS=7 MAX=20  # CLI 検索
make convert                          # CSV → Excel 変換
make ui                               # Web UI 起動
make test                             # テスト実行
make clean                            # data/csv, data/excel を削除
```

## 対応カテゴリ

`cs.AI`, `cs.CL`, `cs.CV`, `cs.LG`, `cs.RO`, `cs.NE`, `cs.IR`, `cs.SE`, `stat.ML`, `eess.AS`, `eess.IV`, `math.OC`, `q-bio.QM`, `physics.comp-ph`

## 出力ディレクトリ

```
data/
├── csv/    # 検索結果 CSV
├── excel/  # 変換後の Excel
└── pdf/    # ダウンロードした PDF
```

## テスト

```bash
uv run pytest tests/ -v          # 全テスト実行
uv run pytest tests/ -v --cov   # カバレッジ付き
```

## プロジェクト構成

```
arxiv_hunt/
├── arxiv_hunt/          # ライブラリ本体
│   ├── client.py        #   arXiv API クライアント
│   ├── config.py        #   設定定数
│   ├── csv_io.py        #   CSV 読み書き
│   ├── database.py      #   SQLite DB (FTS5 全文検索)
│   ├── downloader.py    #   PDF ダウンロード
│   ├── excel_converter.py #  Excel 変換
│   ├── bibtex.py        #   BibTeX / RIS エクスポート
│   ├── models.py        #   Paper データモデル
│   ├── tags.py          #   タグ管理
│   └── watcher.py       #   定期検索 & Slack 通知
├── scripts/             # CLI エントリポイント
├── ui/                  # Streamlit Web UI
├── tests/               # テストスイート
├── data/                # 出力ファイル (Git 管理外)
├── pyproject.toml
└── Makefile
```
