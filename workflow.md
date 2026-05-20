# arxiv_hunt 次期機能検討ワークフロー

**作成日:** 2026-02-26
**手法:** ユーザーペルソナ x SIerペルソナ 対話型要件定義

---

## 参加者

| ロール | ペルソナ | 視点 |
|--------|----------|------|
| **User** | 情報科学研究科 D2（NLP/LLM専攻）、ほぼ毎日利用 | 研究ワークフロー・実用性 |
| **SIer** | システムインテグレーター技術評価チーム | 技術的実現性・品質・保守性 |

---

## 対話ログ

### Round 1: 最も切実な課題

**User:**
> 毎日arXivの新着をチェックしているが、検索した後の論文管理が全くできない。
> CSV出力して終わりなので、結局Zoteroに戻ってしまう。具体的に3つ困っている:
> 1. PDFを手動でブラウザからダウンロードしている
> 2. 「3週間前に見つけたあの論文」を探せない（履歴が5件しかない）
> 3. 論文にタグを付けて管理できない

**SIer:**
> 根本原因はデータ永続化がCSVファイルベースであることです。現状の `csv_io.py` は
> `MAX_ARCHIVES = 5` で古いアーカイブを物理削除しており、過去データが失われます。
> SQLite導入で履歴・タグ・ブックマーク全てを解決できます。ただし、**テストカバレッジが
> 0%の状態でDB導入するのは極めてリスクが高い**ため、テスト整備を先行させるべきです。

**User:**
> テストの重要性は理解するが、ユーザーとしてはまずPDFダウンロードが欲しい。
> 学会出張前にオフラインで読む論文をまとめて取得したい場面が週1-2回ある。

**SIer:**
> PDFダウンロードは `arxiv` ライブラリの `result.download_pdf()` メソッドで実装可能で、
> 技術的難易度は低いです（3人日）。`config.py` に `PDF_OUTPUT_DIR` が既に定義済みなので
> 設計意図はあったようです。テスト整備と並行して進められます。

---

### Round 2: 日々のワークフロー効率化

**User:**
> 毎朝同じクエリを手動で打つのが非効率。定期自動巡回+Slack通知があれば
> 研究室全体の情報共有にもなる。あと、BibTeXエクスポートがないと論文執筆時に
> 結局arXivページを開き直す必要がある。

**SIer:**
> 定期自動巡回はcron + CLI連携で実現可能ですが、通知機能（Slack/メール）は
> 外部サービス依存が増えます。まずCLIのJSON出力対応（`--format json`）を実装し、
> パイプラインで自由に連携できるようにする方が汎用的です。
>
> BibTeXエクスポートは `Paper` dataclass のフィールドから生成するだけなので
> 低工数（2人日）で対応可能。arXiv IDからBibTeXキーを自動生成し、
> CSV/Excelと同様にダウンロードボタンを追加すればよいでしょう。

**User:**
> JSON出力は確かに便利。`jq` と組み合わせて自動化スクリプトに組み込みたい。
> ただ通知機能は研究室運用上かなり重要。最低限Slack Webhookだけでも対応してほしい。

**SIer:**
> Slack Webhook連携は `httpx` で POST するだけなので追加1人日で対応可能です。
> ただし、Webhook URLの管理は `.env` で行い、コードにハードコードしない設計が必須。
> これは提案16（python-dotenv導入）との依存関係になります。

---

### Round 3: UI/UX改善

**User:**
> Web UIで検索結果を眺めているとき、その場でアブストラクトの日本語訳を
> 見たい。ExcelのTRANSLATE数式は便利だが、スクリーニング時は母語の方が
> 圧倒的に速い。あと200件表示するとStreamlitが重くなる。

**SIer:**
> ページネーションは `st.session_state` にページ番号を保持するだけで実装可能（3人日）。
> リアルタイム翻訳は翻訳APIの選定が重要です:
> - Google Translate API: 有料だが高品質
> - DeepL API: 学術テキストに強い、無料枠あり
> - ローカルLLM（Ollama）: オフライン対応、レイテンシに注意
>
> UIにはトグルスイッチ（原文/翻訳）を配置し、翻訳結果はキャッシュする設計を推奨。

**User:**
> 検索プリセットも自分でカスタマイズしたい。現状ハードコードされている3つだけでは
> 自分の研究テーマ（Instruction Tuning + RLHF + Alignment）に合わない。

**SIer:**
> `config.py` の `SEARCH_PRESETS` を外部設定ファイル（YAML/JSON）に移動し、
> UI上でプリセットの追加・編集・削除を可能にします。DB導入後はプリセットも
> DBに保存して永続化できます。工数は設定ファイル版で1人日、DB版で追加2人日。

---

### Round 4: 学術ツールとしての拡張

**User:**
> Connected Papersのような引用関係の可視化が理想。サーベイ論文を書く際、
> 関連研究の網羅性を確認するのに必須。あとSemantic ScholarやDBLPとの
> 連携で、arXiv版と会議版の差異も把握したい。

**SIer:**
> Semantic Scholar Academic Graph API は無料で被引用数・関連論文・
> 影響力指標を取得できます（1秒あたり100リクエスト）。arXiv IDをキーに
> `citationCount`, `referenceCount`, `influentialCitationCount` を取得し、
> 検索結果にバッジ表示+被引用数ソートを追加します（5人日）。
>
> 引用グラフの可視化は `plotly` や `pyvis` で実装可能ですが、工数が
> 膨らむため（8人日+）、まずはテキストベースの引用/被引用リスト表示を推奨。

**User:**
> 段階的アプローチに同意する。まずは被引用数の表示だけでもサーベイの
> 質が大きく上がる。あと著者のh-indexや所属機関も知りたい。
> arXivのプレプリントは査読なしなので、著者の実績が重要な判断材料。

**SIer:**
> 著者プロフィールは Semantic Scholar Author API で取得可能です。
> ただし著者名の曖昧さ（同姓同名）の解決が技術的に難しく、ORCID連携や
> Semantic Scholar Author IDでの紐づけが必要。優先度は低めに設定し、
> Phase 5以降での対応を推奨します。

---

### Round 5: 技術基盤と運用

**User:**
> テストが空なのはユーザーとしても不安。CSVインジェクション防止のような
> セキュリティ機能が壊れたら困る。アップデート時のデグレが怖い。

**SIer:**
> 全面的に同意です。テストカバレッジ0%は**致命的**な技術的負債です。
> 具体的なテスト計画:
> - `models.py`: `Paper.from_arxiv_result` のフィールドマッピング検証
> - `csv_io.py`: `_sanitize_cell` のインジェクション防止テスト、ファイルI/O
> - `client.py`: arXiv API呼び出しのモック化テスト
> - `excel_converter.py`: Excel生成結果の検証
> - `search_form.py`: `_validate_input` のバリデーションテスト
>
> 目標カバレッジ80%以上、CI/CDで自動実行。これを**全ての機能追加に先行**させます。

**User:**
> 研究室の他のメンバーにも使ってもらいたいが、セットアップが面倒。
> Dockerで一発で立ち上がると嬉しい。

**SIer:**
> Docker化は3人日で対応可能です。`python:3.12-slim` ベースで、
> `uv` による依存解決 -> Streamlit UI起動の2ステージビルド。
> `docker-compose.yml` でポートマッピングとデータ永続化も設定します。
> ただしphase 3以降（環境変数管理の整備後）が適切です。

---

### Round 6: 論文の読了管理

**User:**
> 「未読」「読みかけ」「精読済み」のステータスを管理したい。積読が増える
> 一方で進捗が見えない。カンバンボード形式で視覚的に管理できると嬉しい。
> あと、論文メモ（感想・疑問点・自分の研究との関連）をツール内で完結させたい。

**SIer:**
> DB導入を前提に、`papers` テーブルに `status` カラム（未読/読中/精読済/要再読）と
> `notes` テーブル（論文ごとの自由テキストメモ）を追加します。
> カンバンUIは Streamlit のカラムレイアウト + ドラッグ&ドロップで実装可能ですが、
> Streamlit標準では制約があるため、`streamlit-sortables` 等の外部コンポーネントが
> 必要です。まずはリスト表示+ステータスセレクタから始めるのが現実的（3人日）。

---

### Round 7: 参考文献抽出（Reference Extraction）

**User:**
> サーベイ論文を書く際、ある論文が引用している参考文献を一覧で取得したい。
> Connected Papersのような可視化まではいらないが、「この論文が何を引用しているか」を
> 構造化データとして取得できれば、関連研究の芋づる式探索が格段に効率化する。
> GROBIDでPDFから参考文献を抽出したい。

**SIer:**
> GROBIDはSemantic Scholar、ResearchGate、Internet Archive等でも本番採用されている
> プロダクションレベルのPDF構造化ツールです。参考文献抽出の精度はF1≒0.87-0.90（DLモデル時）。
> arxiv_huntには既にPDF一括ダウンロード（F03）が実装済みなので、
> **PDFを入力 → GROBIDで参考文献を構造化抽出** のパイプラインは自然な拡張です。

#### アプローチ比較（参考）

| 評価軸 | GROBID（採用） | Semantic Scholar API（参考） |
|--------|---------------|---------------------------|
| **セットアップ** | Docker推奨（`docker run lfoppiano/grobid`） | REST API、認証不要 |
| **追加依存** | grobid-client-python + GROBIDサーバー | httpx のみ |
| **前提条件** | PDF DL済み（F03 ✅ 実装済み） | arXiv IDのみ |
| **精度** | F1≒0.87-0.90（DLモデル使用時） | Semantic Scholar DBのカバレッジ依存 |
| **新着論文対応** | 即座（PDFがあれば） | 数日遅延あり |
| **オフライン対応** | 可能（ローカルサーバー） | 不可 |
| **arXiv外PDF対応** | 可能（任意のPDF） | arXiv / DOI等の外部ID必須 |
| **出力** | TEI/XML → パース → 構造化データ | JSON（即利用可） |
| **インフラコスト** | Javaヒープ4-8GB推奨 | 無料 |

#### SIer技術評価

> GROBIDを主軸にする利点:
>
> 1. **F03（PDF DL）が実装済み** — PDFは既に手元にある前提を活用
> 2. **外部API非依存** — Semantic Scholar APIのカバレッジ遅延や障害に依存しない
> 3. **arXiv外PDF対応** — 学会PDF等からの参考文献抽出にも拡張可能（F23と相乗効果）
> 4. **オフライン対応** — 出張・移動時にもローカルGROBIDサーバーで動作
> 5. **プロダクション実績** — Semantic Scholar自体がGROBIDを内部利用している
>
> 留意点:
> - GROBIDサーバーの起動が必要（Docker推奨: `docker run -p 8070:8070 lfoppiano/grobid:0.8.1`）
> - TEI/XMLのパースが必要（`lxml` or `xml.etree.ElementTree` で対応可能）
> - 初回起動時にモデルロードで10-30秒のウォームアップあり

**User:**
> GROBIDで行く。PDF DLが既にあるのでパイプラインとしても綺麗。
> 参考文献を自分のDBに取り込んで、そこからさらに深掘りできる
> 「芋づる式サーベイ」の起点になるのが理想。

---

## F34: 参考文献抽出（GROBID） — 詳細仕様

### 概要

検索結果から論文を1本選択し、ダウンロード済みPDFをGROBIDに送信して
参考文献（references）を構造化抽出・表示・DB保存する機能。

### ユーザーストーリー

```
サーベイを書いているD2学生として、
検索で見つけた論文の参考文献一覧をPDFから抽出したい。
それにより、関連研究を芋づる式に探索し、サーベイの網羅性を高めたい。
```

### GROBID API設計

```
GROBID REST API（ローカルサーバー）
Base URL: http://localhost:8070/api

1. 参考文献抽出（推奨エンドポイント）
   POST /processReferences
   Content-Type: multipart/form-data
   Body: input = @paper.pdf
   Response: TEI/XML（参考文献セクションのみ）

2. フルドキュメント解析（代替）
   POST /processFulltextDocument
   Content-Type: multipart/form-data
   Body: input = @paper.pdf
   Response: TEI/XML（全文構造化、参考文献を含む）
```

### TEI/XML パース対象（参考文献）

```xml
<listBibl>
  <biblStruct xml:id="b0">
    <analytic>
      <title level="a">Attention Is All You Need</title>
      <author><persName><forename>Ashish</forename><surname>Vaswani</surname></persName></author>
      ...
    </analytic>
    <monogr>
      <title level="m">Advances in Neural Information Processing Systems</title>
      <imprint><date>2017</date></imprint>
    </monogr>
    <idno type="DOI">10.48550/arXiv.1706.03762</idno>
    <idno type="arXiv">1706.03762</idno>
  </biblStruct>
  ...
</listBibl>
```

### DBスキーマ追加

```sql
-- 参考文献リレーション（論文A が 論文B を引用）
CREATE TABLE IF NOT EXISTS paper_references (
    source_paper_id  INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id   INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    context          TEXT    NOT NULL DEFAULT '',   -- 引用箇所テキスト（本文中の言及）
    fetched_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_paper_id, cited_paper_id)
);
```

### モジュール構成

```
arxiv_hunt/
  grobid_client.py ... GROBIDサーバー連携
                       - GrobidClient class
                         - __init__(base_url="http://localhost:8070")
                         - is_alive() -> bool                    # サーバーヘルスチェック
                         - extract_references(pdf_path) -> list[Reference]
                       - TEI/XMLパーサー
                         - parse_tei_references(xml_str) -> list[Reference]
                       - Reference dataclass:
                         - title: str
                         - authors: str          # セミコロン区切り
                         - year: str
                         - venue: str            # ジャーナル/会議名
                         - doi: str
                         - arxiv_id: str         # あれば
                         - raw_text: str         # 非構造化テキスト（フォールバック）

tests/
  test_grobid_client.py ... GROBIDクライアントテスト
                            - TEI/XMLパース単体テスト（モックXML）
                            - GROBIDサーバーAPIモックテスト
                            - DB統合テスト
```

### 実装タスク分割（エージェント協調: 基本3体）

| タスク | 担当エージェント | 内容 | 前提 |
|--------|-----------------|------|------|
| T1: Reference dataclass + TEIパーサー | Agent A（テスト基盤） | grobid_client.py: Reference, parse_tei_references() | — |
| T2: GROBIDクライアント実装 | Agent B（バックエンド） | grobid_client.py: GrobidClient class, API通信 | T1 |
| T3: DBスキーマ拡張 | Agent B（バックエンド） | database.py: paper_references テーブル + CRUD | T1 |
| T4: テスト実装 | Agent A（テスト基盤） | test_grobid_client.py: XMLパース + APIモック + DB統合 | T1,T2,T3 |
| T5: CLI統合 | Agent C（機能開発） | scripts/: --references オプション追加 | T2,T3 |
| T6: UI統合 | Agent C（機能開発） | ui/components/: 参考文献表示パネル | T2,T3 |

### GROBIDサーバー起動方法

```bash
# Docker（推奨）
docker run --rm -p 8070:8070 lfoppiano/grobid:0.8.1

# ヘルスチェック
curl http://localhost:8070/api/isAlive
# => 200 OK
```

### UI仕様（Streamlit）

```
検索結果テーブル
  └─ [論文タイトル] クリック or 「参考文献を抽出」ボタン
      ├─ GROBIDサーバー接続チェック（未起動時はガイダンス表示）
      ├─ PDF未DL時は自動ダウンロード（F03連携）
      └─ 参考文献パネル（展開表示）
          ├─ 件数サマリ: "42 references found"
          ├─ ソート: 年順 / タイトル順
          ├─ 各参考文献:
          │   ├─ タイトル
          │   ├─ 著者 / 年 / venue
          │   ├─ DOI / arXiv ID（あれば、リンク付き）
          │   └─ [DBに追加] [BibTeX] ボタン
          └─ 一括操作: [全てDBに追加] [BibTeXエクスポート]
```

### config.py 追加設定

```python
# GROBID settings
GROBID_BASE_URL = "http://localhost:8070"
GROBID_TIMEOUT_SECONDS = 60
GROBID_PROCESS_REFERENCES_ENDPOINT = "/api/processReferences"
```

---

## 機能一覧（必要度別）

### 必要度: 大（ないと実用に耐えない / 非常に高頻度で必要）

| # | 機能 | User視点の理由 | SIer技術評価 | 工数 | 状態 |
|---|------|----------------|--------------|------|------|
| F01 | **テストスイート整備** | デグレ防止、ツール信頼性 | カバレッジ0%は致命的。全改修の前提条件 | 8人日 | **実装済み** ✅ |
| F02 | **SQLiteデータベース導入** | 過去論文の検索、履歴無制限化 | ファイルベースの限界。タグ/ブックマーク/メモの基盤 | 8人日 | **実装済み + Web UI 配線済 (Library ページ)** ✅ |
| F03 | **PDF一括ダウンロード** | オフライン閲読、出張・移動時の必需品 | `arxiv` ライブラリの既存メソッド活用。低難易度 | 3人日 | **実装済み + Web UI 配線済 (Download PDFs (ZIP))** ✅ |
| F04 | **タグ付け・ラベリング** | 「要精読」「サーベイ用」等の分類管理 | DB前提。`tags` + `paper_tags` テーブル設計 | 4人日 | **実装済み + Web UI 配線済 (結果カードの Tags 入力 / Library の Browse by tag)** ✅ |
| F05 | **BibTeX/RISエクスポート** | 論文執筆時の必須出力形式 | Paper dataclassから生成。低工数 | 2人日 | **実装済み + Web UI 配線済 (Download BibTeX / RIS)** ✅ |
| F06 | **CI/CDパイプライン構築** | （間接的に品質・信頼性向上） | GitHub Actions。テスト+リント+型チェック自動化 | 3人日 | 未着手 |
| F07 | **定期自動巡回+通知** | 毎朝の手動チェック廃止、論文見逃し防止 | cron + CLI + Slack Webhook。JSON出力が前提 | 5人日 | **実装済み** ✅ |
| F08 | **脆弱性スキャン導入** | （セキュリティ基盤） | Dependabot + pip-audit。CI組み込みで1人日 | 1人日 | 未着手 |
| F09 | **静的型チェック導入** | （コード品質基盤） | mypy strict mode。型ヒント基盤は既にある | 2人日 | **実装済み** ✅ |

**小計: 36人日（うち実装済み 30人日）**

---

### 必要度: 中（あると効率が大幅に上がる / 週に数回使いたい）

| # | 機能 | User視点の理由 | SIer技術評価 | 工数 | 状態 |
|---|------|----------------|--------------|------|------|
| F10 | **検索結果ページネーション** | 大量結果時のUI性能改善 | `st.session_state` でページ管理。中難易度 | 3人日 | 未着手 |
| F11 | **リアルタイム翻訳表示** | スクリーニング速度向上（母語の優位性） | DeepL/Google API連携 + キャッシュ | 5人日 | 未着手 |
| F12 | **引用関係・被引用数表示** | サーベイの網羅性確認 | Semantic Scholar API連携 | 5人日 | 未着手 |
| F13 | **論文メモ・アノテーション** | 読後の感想・疑問をツール内で管理 | DB前提。`notes` テーブル + 全文検索 | 3人日 | 未着手 |
| F14 | **読了状態・進捗管理** | 積読管理、ステータス可視化 | DB前提。リスト+セレクタUIから段階的に | 3人日 | 未着手 |
| F15 | **プリセットカスタマイズ** | 自分の研究テーマに合わせた保存 | YAML/JSON外部設定化 -> DB化 | 3人日 | 未着手 |
| F16 | **JSON出力・パイプライン連携** | CLIの自動化・jq連携 | `--format json` オプション追加 | 2人日 | 未着手 |
| F17 | **高度な検索構文** | AND/OR/NOT明示的記述 | arXiv APIのクエリ構文対応。UIガイド追加 | 3人日 | 未着手 |
| F18 | **カスタム例外クラス設計** | エラー時の適切なガイダンス | `exceptions.py` 新設。全モジュール改修 | 2人日 | 未着手 |
| F19 | **検索結果キャッシュ** | 同一クエリの再検索高速化 | `@st.cache_data` + DB保存 | 3人日 | 未着手 |
| F20 | **python-dotenv導入** | 環境ごとの設定切替 | `.env`読み込み。config.py改修 | 1人日 | 未着手 |
| F21 | **構造化ログ** | トレーサビリティ向上 | `python-json-logger` + RotatingFileHandler | 2人日 | 未着手 |
| F22 | **Docker化** | チームメンバーへの簡易展開 | マルチステージビルド + compose | 3人日 | 未着手 |
| F23 | **arXiv以外のソース対応** | 査読済み会議版の確認 | DBLP/OpenReviewリンク生成から段階的に | 5人日 | 未着手 |
| F24 | **LLMによる論文要約** | 大量新着の高速スクリーニング | Ollama/OpenAI API連携。PDF取得が前提 | 5人日 | 未着手 |
| F25 | **GitHub Issues連携** | 読書管理ワークフロー自動化 | PyGithub + Issue テンプレート | 5人日 | 未着手 |
| **F34** | **参考文献抽出（GROBID）** | **芋づる式サーベイの起点。PDF→参考文献構造化抽出** | **GROBID主軸。F02+F03前提（両方実装済み）** | **5人日** | **NEW** |

**小計: 58人日**

---

### 必要度: 小（あると嬉しい / ときどき便利）

| # | 機能 | User視点の理由 | SIer技術評価 | 工数 | 状態 |
|---|------|----------------|--------------|------|------|
| F26 | **類似論文レコメンデーション** | サーベイの見落とし防止 | 埋め込みベクトル（Specter等）。高難易度 | 8人日 | 未着手 |
| F27 | **Zotero/Mendeley連携** | 既存文献管理ツールとのシームレス連携 | Zotero Web API。認証管理が必要 | 5人日 | 未着手 |
| F28 | **著者プロフィール表示** | 著者実績による論文信頼性判断 | Semantic Scholar Author API。同姓同名問題あり | 4人日 | 未着手 |
| F29 | **検索結果共有URL** | ゼミ・Slackでの論文リスト共有 | URLパラメータによるクエリ状態復元 | 3人日 | 未着手 |
| F30 | **検索クエリオートコンプリート** | 過去クエリの再利用効率化 | DB前提。外部コンポーネント検討 | 4人日 | 未着手 |
| F31 | **非同期処理・並行検索** | 大量検索時のパフォーマンス | ThreadPoolExecutor + Semaphore。高難易度 | 5人日 | 未着手 |
| F32 | **CrossRef連携（DOI解決）** | 正式出版版のDOI取得、citation充実 | CrossRef REST API。曖昧マッチの精度課題 | 4人日 | 未着手 |
| F33 | **Ruffリンター導入** | コードスタイル統一 | pyproject.toml設定追加のみ | 1人日 | 未着手 |
| **F35** | **Semantic Scholar APIフォールバック** | **GROBID未起動時のAPI代替、被引用数付加** | **F34前提。httpxのみで軽量** | **3人日** | **NEW** |

**小計: 37人日**

---

## 推奨ロードマップ

```
Phase 1 [Week 1-2] 基盤整備 ── ✅ 完了（実施日: 2026-02-26）
  ├─ F01 テストスイート整備 ............ 8人日  ✅ 実装済み（90テスト, 87%カバレッジ）
  ├─ F09 静的型チェック導入 ............ 2人日  ✅ 実装済み（mypy 0エラー）
  ├─ F33 Ruffリンター導入 .............. 1人日  （未着手）
  ├─ F20 python-dotenv導入 ............. 1人日  （未着手）
  └─ F06 CI/CDパイプライン構築 ......... 3人日  （未着手、git環境前提）

Phase 2 [Week 3-4] データ基盤+即効性の高い機能 ── ✅ 完了（実施日: 2026-02-26）
  ├─ F02 SQLiteデータベース導入 ........ 8人日  ✅ 実装済み（FTS5全文検索対応）
  ├─ F03 PDF一括ダウンロード ........... 3人日  ✅ 実装済み（レート制限付き）
  ├─ F05 BibTeX/RISエクスポート ........ 2人日  ✅ 実装済み
  ├─ F16 JSON出力・パイプライン連携 .... 2人日  （未着手）
  └─ F18 カスタム例外クラス設計 ........ 2人日  （未着手）

Phase 3 [Week 5-7] ユーザー体験向上
  ├─ F04 タグ付け・ラベリング .......... 4人日  ✅ 実装済み（F02前提→充足）
  ├─ F07 定期自動巡回+通知 ............ 5人日  ✅ 実装済み（Slack Webhook対応）
  ├─ F10 検索結果ページネーション ...... 3人日  （未着手）
  ├─ F13 論文メモ・アノテーション ...... 3人日  （未着手、F02前提→充足）
  ├─ F14 読了状態・進捗管理 ............ 3人日  （未着手、F02前提→充足）
  └─ F15 プリセットカスタマイズ ........ 3人日  （未着手）

Phase 4 [Week 8-10] 学術機能拡張 ── ★ F34を最優先で追加
  ├─ F34 参考文献抽出（GROBID）......... 5人日  ★ 次期実装対象
  │   ├─ Phase 4A: GROBIDクライアント+TEIパーサー .. 3人日
  │   └─ Phase 4B: UI統合+DB連携 .................. 2人日
  ├─ F12 引用関係・被引用数表示 ........ 5人日
  ├─ F11 リアルタイム翻訳表示 .......... 5人日
  ├─ F17 高度な検索構文 ................ 3人日
  └─ F23 arXiv以外のソース対応 ........ 5人日

Phase 5 [Week 11-13] 運用基盤+追加機能
  ├─ F22 Docker化 ...................... 3人日
  ├─ F24 LLMによる論文要約 ............ 5人日  （F03前提→充足）
  ├─ F25 GitHub Issues連携 ............ 5人日
  ├─ F21 構造化ログ .................... 2人日
  ├─ F08 脆弱性スキャン導入 ............ 1人日
  └─ F19 検索結果キャッシュ ............ 3人日

Phase 6 [随時] 将来拡張
  ├─ F26 類似論文レコメンデーション .... 8人日
  ├─ F27 Zotero/Mendeley連携 .......... 5人日
  ├─ F28 著者プロフィール表示 .......... 4人日
  ├─ F29 検索結果共有URL .............. 3人日
  ├─ F30 検索クエリオートコンプリート .. 4人日
  ├─ F31 非同期処理・並行検索 .......... 5人日
  ├─ F32 CrossRef連携（DOI解決）....... 4人日
  ├─ F33 Ruffリンター .................. （Phase 1 で対応予定）
  └─ F35 Semantic Scholar APIフォールバック .. 3人日（F34前提、GROBID未起動時の代替）
```

### F34 と関連機能の関係性

> - **F34（GROBID参考文献抽出）→ F12（被引用数表示）**: F34 で `paper_references` テーブルを
>   新設し参考文献のDB基盤を構築。F12 では Semantic Scholar API で被引用数を付加する拡張。
> - **F34 → F35（Semantic Scholar APIフォールバック）**: GROBIDサーバー未起動時の代替手段。
>   F34 の Reference dataclass を共有し、取得元を切り替えるだけで統合可能。
> - **F34 → F23（arXiv外ソース対応）**: GROBIDは任意のPDFを処理可能なため、
>   arXiv以外の学会PDF等にも同一パイプラインで対応できる。

---

## 合意事項まとめ

### User と SIer の合意点

1. **テスト整備（F01）が全ての前提** — テストなしの機能追加はリグレッションリスクが極めて高い
2. **SQLite導入（F02）がユーザー機能の基盤** — タグ、メモ、履歴、ブックマーク全ての前提
3. **PDF DL（F03）+ BibTeX（F05）は即効性が高い** — 低工数で研究者の日常ワークフローに直結
4. **翻訳・引用関連は段階的に** — まず被引用数表示、次に翻訳トグル、最後にグラフ可視化
5. **Docker化はPhase 5** — 環境変数管理・DB設計が安定してから

### 残課題・検討事項

- 翻訳API（DeepL vs Google vs ローカルLLM）の選定は PoC で比較検証が必要
- マルチユーザー対応は現時点では見送り（個人〜研究室規模のため）
- モバイル対応（Streamlitの制約上、現時点では非対応）

---

## 総括

| 項目 | 値 |
|------|-----|
| 提案総数 | 35件（+2: F34 GROBID参考文献抽出, F35 Semantic Scholar APIフォールバック） |
| 必要度 大 | 9件（36人日）── **うち7件 実装済み（30人日）** |
| 必要度 中 | 17件（58人日）── F34 追加 |
| 必要度 小 | 9件（37人日）── F35 追加 |
| 総概算工数 | 131人日（約6.5人月） |
| 実装済み工数 | 30人日（Phase 1-2 コア機能） |
| 残工数 | 101人日 |
| 推奨チーム体制 | 開発者2名（バックエンド1名 + フルスタック1名） |
| Phase 1-5 推奨期間 | 約13週間（3ヶ月強） |
| **次期実装推奨** | **F34 参考文献抽出 — GROBID（5人日）** |

> **SIer最終所見:** 現在のarxiv_huntは約1,300行の小規模かつ品質の良いコードベースです。
> CSVインジェクション防止やdataclassによる型安全な設計など、セキュリティ意識の高い実装が
> 評価できます。Phase 1（テスト+CI/CD）を着実に実施した上で、Phase 2（DB+PDF+BibTeX）
> まで完了すれば、「毎日使える論文検索・管理ツール」として実用レベルに到達します。

> **User最終意見:** Phase 2まで完了すれば「検索→保存→管理→論文執筆」のワークフローが
> ツール内で完結する。特にPDF DL + BibTeX + タグ管理の3点セットが揃えば、Zoteroから
> 完全移行する動機になる。定期巡回+Slack通知は研究室運用で強力な差別化要因。

---

## 実装結果（必要度大）

**実施日:** 2026-02-26
**手法:** TDD（テスト駆動開発） x 並列エージェント協調（3ペルソナ）
**除外:** F06 CI/CD, F08 脆弱性スキャン（git系のため対象外）

### 体制

| ロール | ペルソナ | Phase 1 担当 | Phase 2 担当 |
|--------|----------|-------------|-------------|
| 監督役 | PM | 統合検証・品質管理 | 統合検証・スキル保存 |
| Agent A | テスト基盤アーキテクト | テスト基盤+既存テスト | PDFダウンロード |
| Agent B | バックエンドアーキテクト | DB設計+BibTeX実装 | タグ管理ファサード |
| Agent C | 機能開発エンジニア | mypy型チェック導入 | 定期巡回+JSON出力 |

### 実装完了機能

| # | 機能 | ファイル | テスト数 | カバレッジ |
|---|------|----------|---------|-----------|
| F01 | テストスイート整備 | tests/conftest.py, test_*.py (8ファイル) | 90 | 87% |
| F02 | SQLiteデータベース | arxiv_hunt/database.py | 16 | 95% |
| F03 | PDF一括ダウンロード | arxiv_hunt/downloader.py | 12 | 92% |
| F04 | タグ付けシステム | arxiv_hunt/tags.py | 13 | 100% |
| F05 | BibTeX/RISエクスポート | arxiv_hunt/bibtex.py | 10 | 88% |
| F07 | 定期巡回+Slack通知 | arxiv_hunt/watcher.py, formatter.py | 14 | 98%/100% |
| F09 | mypy静的型チェック | pyproject.toml [tool.mypy] | - | 0エラー |

### 検証結果

```
全テスト: 90 passed in 13s
mypy:     Success: no issues found in 12 source files
カバレッジ: 87% (TOTAL 520 stmts, 68 miss)
```

### 新規モジュール一覧

```
arxiv_hunt/
  database.py      ... SQLite DB (papers/searches/tags, FTS5全文検索)
  downloader.py    ... PDF一括ダウンロード (urllib, rate limit)
  bibtex.py        ... BibTeX/RIS形式エクスポート
  tags.py          ... タグ管理ファサード (DB操作のラッパー)
  formatter.py     ... JSON出力フォーマッター
  watcher.py       ... 定期巡回エンジン (YAML設定, Slack通知)
tests/
  conftest.py      ... 共通フィクスチャ
  test_models.py   ... Paper dataclass テスト (6)
  test_csv_io.py   ... CSV I/O テスト (14)
  test_excel_converter.py ... Excel変換テスト (5)
  test_database.py ... DB テスト (16)
  test_downloader.py ... PDF DL テスト (12)
  test_bibtex.py   ... BibTeX テスト (10)
  test_tag_cli.py  ... タグ管理テスト (13)
  test_watcher.py  ... 巡回+JSON テスト (14)
```

### 保存したスキル（/workspace/skills/）

| スキル | 内容 |
|--------|------|
| tdd_python_module.md | TDDでPythonモジュールを実装する標準手順 |
| parallel_agent_coordination.md | 並列エージェント協調パターン |
| sqlite_tdd_pattern.md | SQLite + FTS5 の TDD パターン |
