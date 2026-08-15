# Building Advanced Agentic Systems on AWS - ハンズオンガイド

## コース概要

このハンズオンガイドは「Building Advanced Agentic Systems on AWS」研修コースの各モジュールに対応した実践的なシナリオと手順を提供します。各ハンズオンで作成したリソースやソリューションは、研修中のデモとして受講者に見せることができます。

## コースの日程構成

| モジュール | テーマ | ハンズオン時間 |
|-----------|--------|--------------|
| M01 | マルチエージェントアーキテクチャと通信パターン（Strands SDK・Workflow/Graph/Swarm・MCP） | 60分 |
| M02 | コンテキストエンジニアリングとパフォーマンスの最適化（圧縮・キャッシュ・メモリ管理） | 45分 |
| M03 | セキュリティとコンプライアンスの実装（AgentCore Identity/Policy・VPC統合・監査） | 45分 |
| ラボ | Amazon Bedrock AgentCore にエージェントをデプロイする | - |
| M04 | 本番環境のモニタリング、オブザーバビリティ、評価（トレーシング・評価フレームワーク） | 45分 |
| M05 | Well-Architected エージェンティック AI システム（設計アクティビティ） | 45分 |

## 前提条件

### 環境要件
- AWS アカウント（管理者アクセス）
- AWS CLI v2 設定済み
- Python 3.12+
- Node.js 18+
- AWS SAM CLI インストール済み
- Amazon Bedrock モデルアクセス有効化済み
  - Amazon Nova Lite / Pro
  - Anthropic Claude Sonnet 4

### Python パッケージ
- `boto3`
- `strands-agents` / `strands-agents-tools`
- `bedrock-agentcore` / `bedrock-agentcore-starter-toolkit`
- `opentelemetry-api` / `opentelemetry-sdk`
- `requests`

### リージョン
- 推奨: `us-east-1`（バージニア北部）または `us-west-2`（オレゴン）
- Bedrock AgentCore の全機能が利用可能なリージョンを選択してください

## フォルダ構造

```
handson/
├── README.md                           # このファイル
├── cleanup_all.sh                      # 全リソース一括削除スクリプト
├── M01-multi-agent/                    # マルチエージェントアーキテクチャ
│   ├── scenario.md                     # シナリオ説明
│   ├── steps.md                        # ハンズオン手順
│   ├── workflow_pattern.py             # Workflow パターン実装
│   ├── graph_pattern.py                # Graph パターン実装
│   ├── swarm_pattern.py                # Swarm パターン実装
│   ├── shared_memory_demo.py           # AgentCore Memory 共有デモ
│   └── mcp_tool_agent.py              # MCP ツールとしてのエージェント
├── M02-context-engineering/            # コンテキストエンジニアリング
│   ├── scenario.md
│   ├── steps.md
│   ├── context_optimization.py         # 入力形式の最適化（TOON）
│   ├── prompt_caching.py              # プロンプトキャッシュ実装
│   ├── summarizing_manager.py         # SummarizingConversationManager
│   └── context_isolation.py           # コンテキスト分離（専門エージェント）
├── M03-security-compliance/            # セキュリティとコンプライアンス
│   ├── scenario.md
│   ├── steps.md
│   ├── agentcore_identity_demo.py     # AgentCore Identity 設定
│   ├── agentcore_policy_demo.py       # AgentCore Policy（Cedar）
│   ├── guardrails_demo.py            # Bedrock Guardrails 統合
│   └── audit_logging.py              # 監査ログ実装
├── M04-observability-evaluation/       # モニタリング・オブザーバビリティ・評価
│   ├── scenario.md
│   ├── steps.md
│   ├── otel_tracing.py               # OpenTelemetry トレーシング
│   ├── cloudwatch_dashboard.py        # CloudWatch ダッシュボード
│   ├── agent_evaluation.py            # エージェント評価フレームワーク
│   └── evaluation-dataset.jsonl       # 評価データセット
├── M05-well-architected/              # Well-Architected 設計アクティビティ
│   ├── scenario.md
│   └── steps.md
```

## 使い方

1. 各モジュールフォルダ内の `scenario.md` でシナリオと学習目標を確認
2. `steps.md` の手順に従ってハンズオンを実施
3. Python スクリプトがある場合は実行してデモ動作を確認
4. 終了後は下記クリーンアップ手順に従ってリソースを削除

## クリーンアップ

全モジュールで作成したリソースを一括で削除するスクリプトを用意しています。

### EC2 ハンズオン環境での実行

```bash
cd ~/handson
bash cleanup_all.sh
```

### 対象リソース一覧

| モジュール | 削除対象 |
|-----------|---------|
| M01 | CloudFormation スタック (`m01-multi-agent`)、AgentCore Memory セッション |
| M02 | AgentCore Memory レコード、プロンプトキャッシュ |
| M03 | AgentCore Policy ストア、Guardrail、IAM ロール |
| M04 | CloudWatch ダッシュボード・アラーム、ロググループ、評価ジョブ |
| M05 | ローカル実行のみ（AWS リソースなし） |

### 注意事項

- スクリプトは冪等です（リソースが存在しなければスキップします）
- 実行前に `aws sts get-caller-identity` で正しいアカウントか確認してください

## コスト管理

- 各ハンズオンの推定コスト: $1〜$5
- 使用後は必ずリソースを削除してください
- Bedrock のモデル呼び出しコストが主な費用です（Nova Lite は特に安価）

## トラブルシューティング

### Bedrock モデルアクセスエラー
```
AccessDeniedException: You don't have access to the model
```
→ AWS コンソール → Bedrock → Model access で該当モデルを有効化

### AgentCore 関連エラー
```
ResourceNotFoundException: Agent not found
```
→ AgentCore がリージョンで利用可能か確認。`us-east-1` または `us-west-2` を推奨

### リージョン未対応エラー
→ `us-east-1` または `us-west-2` に変更してください

### トークン上限エラー
→ `maxTokens` パラメータを減らすか、入力プロンプトを短縮
