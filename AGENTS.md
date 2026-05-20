# AGENTS.md

このリポジトリで Claude Code / Codex / その他の AI エージェント（以下「エージェント」）が
作業するときの共通指示。`openspec init` で配置される `.claude/skills/openspec-*/SKILL.md` と
`.claude/commands/opsx/*.md` は英語のまま運用するが、本ファイルの指示が**優先**する。

## 言語

- ユーザーへの応答、確認、要約、コミットメッセージはすべて**日本語**で書く。
- OpenSpec が生成する成果物（`openspec/changes/<name>/` 配下の `proposal.md` /
  `design.md` / `tasks.md` と、`openspec/specs/<capability>/spec.md`）の本文も
  **日本語**で書く。
- ただし以下は**英語のまま温存**する。これらは OpenSpec の validator や下流ツールが
  字句として認識するため、翻訳すると壊れる:
  - 規範動詞 `SHALL` / `MUST` / `SHALL NOT` / `MUST NOT`
  - 見出しプレフィックス `## Purpose` / `## Requirements` / `### Requirement:` /
    `#### Scenario:`
  - GIVEN / WHEN / THEN / AND の太字キーワード
  - コードブロック、ファイルパス、シンボル名、コマンド、URL
- 日本語文中に `SHALL` を埋め込むときは `〜しなければならない (SHALL)` のように
  括弧で添えるか、`〜 SHALL 〜` の形で温存してよい。

## OpenSpec の使い方

- 新規の変更提案は `/opsx:propose` または openspec-propose skill から開始する。
  生成される `proposal.md` / `design.md` / `tasks.md` を日本語で記述する。
- 既存 spec（`openspec/specs/*/spec.md`）を更新するときも、新規追記分は日本語で書く。
- spec の見出し構造（`## Purpose`, `## Requirements`, `### Requirement: <名前>`,
  `#### Scenario: <名前>`）は英語プレフィックスのまま `:` の後ろを日本語にする。
  例: `### Requirement: クエリ合成`
- validator (`openspec validate <name> --type spec --strict`) を変更後に必ず実行し、
  既存と同程度以上のスコアを保つ。

## 既存資産との整合

- `openspec/specs/*/spec.md` と `openspec/specs/README.md` は日本語化済み。新規 spec も
  これに合わせる。
- `.claude/` 配下の skill/command 定義は英語のまま。`openspec update` 等で再生成される
  可能性があるため触らない。日本語化したい場合は本 AGENTS.md 側で指示する。

## レビュー時の確認事項

- 成果物が日本語で書かれているか。
- `SHALL`/`MUST` キーワードと見出しプレフィックスが温存されているか。
- 各 `### Requirement:` ブロックに少なくとも 1 つの `#### Scenario:` が紐づいているか。

## gitの注意事項

- claudeなどのエージェントはコントリビューターにしないこと
- commitは機能で適切に分けること