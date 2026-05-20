# arxiv_hunt — 論文サーベイ

論文をarXivから取得しGitHub Issueで管理するリポジトリです。

## 📋 目的

- 論文を1本ずつIssueで管理し、効率的に読み進める
- キーワードで最新論文を検索できるようにする
- シンプルな運用で継続しやすい仕組みを作る

## 🚀 クイックスタート

### 1. インストール

```bash
cd arxiv_hunt

# 依存関係のインストール（Python 3.9以上が必要）
uv sync

# UI機能を使う場合
uv sync --extra ui
```

### 2. UIの起動

```bash
# 簡単起動
uv run python run_ui.py

# または
make ui
```

ブラウザで http://localhost:8501 が自動的に開きます。

詳細は **[docs/QUICKSTART.md](docs/QUICKSTART.md)** をご覧ください。

## 📖 ドキュメント

- **[クイックリファレンス](QUICK_REFERENCE.md)** - よく使うコマンド一覧
- **[クイックスタート](docs/QUICKSTART.md)** - 5分で始めるガイド
- **[コマンドリファレンス](docs/COMMAND_REFERENCE.md)** - 全コマンドの詳細
- **[ワークフロー](docs/workflow.md)** - 機能追加の流れ
- **[UI実装](docs/UI_IMPLEMENTATION_SUMMARY.md)** - UI実装の詳細

## 🎯 基本的な使い方

### コマンドラインで論文検索

```bash
# VLAに関する論文を検索（CSV形式でdata/csv/に自動保存）
uv run scripts/paperhunt_arxiv.py --query 'all:"vision language action"' --days 14 --max 50

# PDFダウンロード
uv run scripts/download_pdfs.py --input data/csv/results.csv
```

### UIで論文検索

```bash
# UI起動
python run_ui.py
```

サイドバーに `Search` / `History` / `Library` / `Excel Convert` の 4 ページ。

1. `Search` で query / author / categories を指定して検索 (query または author の少なくとも一方が必須 — Categories 単独は弾かれます)。
2. 結果リストから CSV / Excel / BibTeX / RIS / PDF ZIP がダウンロードできます。各カードの `Tags` 入力でローカル DB のタグ編集も可能。
3. `Library` ページで FTS5 全文検索・タグ AND 絞り込み・DB ベースの検索履歴 (`Load`) を利用できます。
4. `History` ページは従来通り CSV アーカイブの直近 5 件 (`Library` とは別)。

なお `scheduled-watch` (定期検索 + Slack POST) は本変更の対象外です。

## 📁 プロジェクト構造

```
arxiv_hunt/
├── README.md              # このファイル
├── pyproject.toml         # プロジェクト設定
├── .env.example           # 環境変数テンプレート
├── .gitignore             # Git除外設定
├── run_ui.py              # UI起動スクリプト
├── Makefile               # 便利コマンド
│
├── docs/                  # ドキュメント
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── workflow.md
│   └── UI_IMPLEMENTATION_SUMMARY.md
│
├── scripts/               # コマンドラインスクリプト
│   ├── paperhunt_arxiv.py
│   ├── download_pdfs.py
│   └── csv_to_excel_translate.py
│
├── ui/                    # Webインターフェース
│   ├── app.py
│   ├── components/
│   └── utils/
│
├── data/                  # データディレクトリ
│   ├── csv/              # 検索結果（Git除外）
│   └── pdf/              # ダウンロードPDF（Git除外）
│
└── .streamlit/           # Streamlit設定
    └── config.toml
```

## 🔍 arXiv検索構文

- `all:"キーワード"` - すべてのフィールドから検索
- `ti:"キーワード"` - タイトルから検索
- `abs:"キーワード"` - アブストラクトから検索
- `au:"著者名"` - 著者から検索
- `cat:カテゴリ` - カテゴリで絞り込み
- `AND`, `OR`, `NOT` - 論理演算子

### 主要なカテゴリ

| カテゴリ | 説明 |
|---------|------|
| cs.RO | Robotics（ロボティクス） |
| cs.AI | Artificial Intelligence（人工知能） |
| cs.CV | Computer Vision（コンピュータビジョン） |
| cs.LG | Machine Learning（機械学習） |
| cs.CL | Natural Language Processing（自然言語処理） |

## 🏷️ Issue管理

### ラベル

| ラベル | 説明 |
|--------|------|
| queue | 読む予定（積み） |
| reading | 読んでいる |
| done | 読み終わり |
| tag/vla | VLA関連 |
| tag/survey | サーベイ論文 |

### ワークフロー

1. **検索** → 良さそうな論文を見つける
2. **Issue作成** → GitHubでIssueを作成
3. **読む** → ラベルをreadingに変更
4. **完了** → ラベルをdoneに変更

## 💡 便利なコマンド

```bash
# UI起動
make ui

# 論文検索
make search

# PDFダウンロード
make download

# テストデータ生成
make test-data

# クリーンアップ
make clean
```

## ⚠️ 注意事項

- PDFファイルは`.gitignore`で追跡対象外です
- arXiv APIの利用制限にご注意ください（スクリプトは自動的に待機します）
- 大量のPDFをダウンロードする場合は、ストレージ容量にご注意ください

## 📚 参考リソース

- [arXiv.org](https://arxiv.org/) - プレプリント論文アーカイブ
- [arXiv API](https://arxiv.org/help/api/) - arXiv API ドキュメント
- [Papers with Code](https://paperswithcode.com/) - 実装付き論文データベース

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

---

**Last Updated**: 2026-02-26
