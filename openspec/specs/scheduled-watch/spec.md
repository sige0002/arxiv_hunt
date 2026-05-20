# scheduled-watch Specification

## Purpose

保存済みの arXiv 検索を 1 つ以上、単一バッチで実行し（典型的には `cron` や
CI スケジューラから）、結果を watch ごとに Slack 風通知メッセージに整形する。

本 capability は通知フローのうち **検索 + メッセージ整形** の前半を担う。
メッセージ送信は意図的に対象外: 整形済み文字列を Slack（あるいは他の
チャネル）に届けるのは呼び出し側責任。

## Scope

スコープ内:
- YAML 設定ファイルから watch エントリのリストをロードする。
- 各 watch を [`search-papers`](../search-papers/spec.md) capability を
  再利用して実行する。
- watch ごとに Slack フレンドリーなメッセージ文字列を生成する。
- `slack_webhook_url` の値をパース後の `WatchConfig` に保持し、整形後に
  呼び出し側が参照できるようにする。

スコープ外:
- 実際の Slack webhook URL への POST。HTTP 層は **今のところ実装されておらず**、
  本仕様にも計画は記録されていない — 呼び出し側（将来の CLI や外部スクリプト）が
  配信を自前で実装する SHALL。
- 既出論文の実行間での重複排除（現状はユーザー責任）。

## Configuration format

本 capability はトップレベルの形が以下のような YAML ファイルを読む SHALL:

```yaml
watches:
  - name: "Robotics manipulation"
    query: 'robot manipulation OR grasping'
    categories: ['cs.RO']         # 省略可、デフォルト []
    days: 1                       # 省略可、デフォルト 1
    max_results: 20               # 省略可、デフォルト 20
  - name: "LLM agents"
    query: 'LLM agent'
    days: 3

slack_webhook_url: "https://hooks.slack.com/services/…"   # 省略可
```

各 watch エントリは `WatchEntry` データクラス 1 つを生成 SHALL。ファイル
全体が `WatchConfig` になる。

## Requirements

### Requirement: Loading the configuration

`load_watch_config(path)` は以下を行う SHALL:

- `path` が存在しなければ `FileNotFoundError` を上げる。
- YAML を `yaml.safe_load` でパースする。
- `watches` 配下の各エントリについて:
  - `name` は必須（無ければ KeyError）。
  - `query` のデフォルトは `""`。
  - `categories` のデフォルトは `[]`。
  - `days` のデフォルトは `1`。
  - `max_results` のデフォルトは `20`。
- トップレベルに `slack_webhook_url` があれば取り込む。無ければ `None`。

### Requirement: Running watches

`run_watch(config)` は以下を行う SHALL:

- `ArxivClient` を 1 つだけ作り、全 watch にまたがって再利用する
  （クライアントのポライトネスディレイが watch 間にも、1 watch 内の
   ページ間にもかかる）。
- 各 watch を宣言順で実行する。呼び出しは
  `client.search(query=…, max_results=…, days=…, categories=… or None)`。
- 各 watch の `name` をキー、`list[Paper]` を値にした dict を返す。

結果が空でも例外を上げない SHALL NOT。空リストはマッチなしの watch に
対する有効な結果。

#### Scenario: Two watches, one empty

- **GIVEN** watch `"A"` と `"B"` を持つ config。`A` のクエリは最近の論文に
  マッチせず、`B` は 3 件マッチする
- **WHEN** `run_watch` を呼び出す
- **THEN** 返却 dict は `"A"` と `"B"` のキーを持つ SHALL
- **AND** `result["A"] == []`
- **AND** `len(result["B"]) == 3`

### Requirement: Slack message format

`format_slack_message(watch_name, papers)` は以下を返す SHALL:

- 空リストの場合: `*{watch_name}*: 新着論文なし (0件)`。
- 非空リストの場合、先頭行は
  `*{watch_name}*: {n}件の新着論文`、続けて最大 10 行、論文 1 件 1 行で:

  ```
    - <{entry_url}|{title}> [{primary_category}] ({arxiv_id})
  ```

- 10 件を超えるときは末尾行 `  ... 他{n-10}件` を付け足す SHALL。

出力は `\n` で連結した単一文字列 SHALL。

#### Scenario: 12 papers, truncation tail appended

- **GIVEN** 入力リストに 12 件の論文
- **WHEN** メッセージを整形する
- **THEN** ヘッダと打ち切り行の間に、論文行がちょうど 10 行出る SHALL
- **AND** 末尾行は `  ... 他2件` SHALL

## Implementation status (informational)

`arxiv_hunt/watcher.py` は config ロード、検索実行、メッセージ整形を
実装する。実際の Slack POST は **実装していない**（`slack_webhook_url`
に対する HTTP クライアントは配線されていない）。`run_watch` を呼ぶ CLI
入口も無いため、現状ではユーザーがプログラムから呼ぶ前提。両方を
追加するのは純粋に追加作業で、上記要件を **拡張** するもので変更ではない。

## Implementation pointers

- `arxiv_hunt/watcher.py` — `WatchEntry`, `WatchConfig`,
  `load_watch_config`, `run_watch`, `format_slack_message`。
- Tests: `tests/test_watcher.py`。
