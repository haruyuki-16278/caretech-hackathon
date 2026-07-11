# GitHub Copilot Instructions

このリポジトリでは、GitHub Copilot のカスタムエージェントを用いた SDD (Specification-Driven Development) を採用しています。

## エージェント

カスタムエージェントは `.github/agents/` ディレクトリに定義されています。詳細は [`AGENTS.md`](../AGENTS.md) を参照してください。

- **orchestrator** (`.github/agents/orchestrator.agent.md`): イシュー作成から PR 作成までの全フローをオーケストレーションします。
- **issue** (`.github/agents/issue.agent.md`): 要件を洗練させ、GitHub Issue を作成・管理します。
- **plan** (`.github/agents/plan.agent.md`): イシューに基づき実装計画を策定します。
- **impl** (`.github/agents/impl.agent.md`): TDD の原則に従い実装を行います。
- **review** (`.github/agents/review.agent.md`): 実装内容をレビューし、フィードバックを提供します。
- **pr** (`.github/agents/pr.agent.md`): プルリクエストを作成します。

## ドキュメント

- [`README.md`](../README.md) - プロジェクトの概要
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) - コントリビューションガイド
- [`docs/`](../docs/) - 詳細なドキュメント
- [`AGENTS.md`](../AGENTS.md) - エージェント構成の説明
