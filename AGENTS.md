# AGENTS.md

このリポジトリでは、GitHub Copilot のカスタムエージェントを使用した AI 駆動の開発フローを採用しています。

## エージェント構成

エージェントファイルは `.github/agents/` ディレクトリに配置されています。

| エージェント | ファイル | 役割 |
|---|---|---|
| オーケストレーター | `.github/agents/orchestrator.agent.md` | 全体フローの管理・サブエージェントの呼び出し |
| イシュー管理 | `.github/agents/issue.agent.md` | Issue の作成・管理・要件の洗練 |
| 実装計画 | `.github/agents/plan.agent.md` | イシューに基づく実装計画の策定 |
| 実装 | `.github/agents/impl.agent.md` | TDD に基づく実装 |
| レビュー | `.github/agents/review.agent.md` | コードレビューとフィードバック |
| プルリクエスト | `.github/agents/pr.agent.md` | PR の作成 |

## 使い方

通常は `orchestrator` エージェントを呼び出すことで、イシューの作成から PR の作成まで一連のフローを自動的に実行します。

## ドキュメント

- [`README.md`](./README.md) - プロジェクトの概要
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) - コントリビューションガイド
- [`docs/`](./docs/) - 詳細なドキュメント
