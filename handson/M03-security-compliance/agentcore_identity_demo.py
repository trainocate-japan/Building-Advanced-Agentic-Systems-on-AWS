"""
モジュール 3: AgentCore Identity - 認証と認可の設定

AgentCore Identity を使用してエージェントの認証フローを実装します。

認証パターン:
- インバウンド: ユーザー → AgentCore Runtime（IAM or OAuth）
- アウトバウンド: AgentCore Runtime → ツール/リソース（IAM Role or OAuth Token）

OAuth フロー:
- 2LO (2-Legged): アプリケーション自身のリソースアクセス
- 3LO (3-Legged): ユーザーの代理で動作
"""

import boto3
import json
from datetime import datetime

# =============================================================================
# AgentCore Identity の設定デモ
# =============================================================================

def demo_identity_overview():
    """AgentCore Identity の全体アーキテクチャを説明"""

    print("=" * 70)
    print(" AgentCore Identity: エージェント認証・認可アーキテクチャ")
    print("=" * 70)

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │                  AgentCore Identity フロー                        │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                   │
    │  [インバウンド認証]                                               │
    │  ユーザー ──── AWS IAM Sig V4 ────▶ AgentCore Runtime            │
    │        └──── OAuth Token ─────────▶ AgentCore Gateway            │
    │                                                                   │
    │  [アウトバウンド認証]                                             │
    │  AgentCore Runtime ──── IAM Role ────▶ AWS リソース              │
    │                    └──── OAuth Token ──▶ 外部サービス             │
    │                                                                   │
    │  [AgentCore Gateway のターゲット別認証]                            │
    │  ┌──────────────┬────────────────┬──────────────────────┐       │
    │  │ ターゲット    │ 認証方式        │ ユースケース          │       │
    │  ├──────────────┼────────────────┼──────────────────────┤       │
    │  │ AWS Lambda   │ IAM            │ 内部ツール            │       │
    │  │ MCP サーバー │ OAuth Token    │ 外部 MCP ツール       │       │
    │  │ OpenAPI      │ IAM            │ REST API             │       │
    │  │ Smithy       │ IAM            │ AWS スタイル API     │       │
    │  └──────────────┴────────────────┴──────────────────────┘       │
    └─────────────────────────────────────────────────────────────────┘
    """)


def demo_oauth_2lo():
    """OAuth 2-Legged 認証 (Client Credentials Flow) のデモ"""

    print("\n" + "─" * 70)
    print("  デモ 1: OAuth 2LO (Client Credentials Flow)")
    print("─" * 70)

    print("""
    [シナリオ] エージェントが自身のサービスロールでデータベースにアクセスする

    フロー:
    1. エージェントが Client ID / Client Secret で Token Endpoint にリクエスト
    2. Authorization Server がアクセストークンを発行
    3. エージェントがトークンを使用してリソースにアクセス

    ┌───────────┐         ┌──────────────────┐         ┌──────────┐
    │  Agent    │──(1)───▶│ Auth Server      │         │ Resource │
    │ (Client)  │◀──(2)───│ (Token Endpoint) │         │ Server   │
    │           │──────────────────(3)───────────────▶│          │
    └───────────┘         └──────────────────┘         └──────────┘

    ユースケース:
    - エージェントが内部 DB にアクセス
    - 開発エージェントが GitLab API にアクセス
    - バッチ処理エージェントが外部サービスにアクセス
    """)

    # AgentCore Identity での設定例
    print("  [AgentCore Identity 設定例]")
    credential_config = {
        "credentialProviderType": "OAUTH2",
        "oauth2Config": {
            "grantType": "CLIENT_CREDENTIALS",
            "tokenEndpoint": "https://auth.example.com/oauth/token",
            "clientId": "agent-service-client",
            "scopes": ["read:data", "write:reports"]
        }
    }
    print(f"  {json.dumps(credential_config, indent=4, ensure_ascii=False)}")


def demo_oauth_3lo():
    """OAuth 3-Legged 認証 (Authorization Code Flow) のデモ"""

    print("\n" + "─" * 70)
    print("  デモ 2: OAuth 3LO (Authorization Code Flow)")
    print("─" * 70)

    print("""
    [シナリオ] エージェントがユーザーの代わりにカレンダーアプリにアクセスする

    フロー:
    1. エージェントがユーザーに認可リクエストを送信
    2. ユーザーがスコープを確認し同意
    3. Authorization Server が認可コードを返す
    4. エージェントが認可コードでアクセストークンを取得
    5. エージェントがユーザーの代わりにリソースにアクセス

    ┌──────┐    ┌───────────┐    ┌──────────────────┐    ┌──────────┐
    │ User │◀──▶│  Agent    │───▶│ Auth Server      │───▶│ Resource │
    │      │    │           │◀───│                  │    │ (Calendar)│
    └──────┘    └───────────┘    └──────────────────┘    └──────────┘
      (2)同意     (1)認可要求      (3)認可コード
                  (4)トークン取得   (5)リソースアクセス

    ユースケース:
    - ユーザーのカレンダーに予定を追加
    - ユーザーのメールを送信
    - ユーザーの Google Drive にファイルを保存
    """)

    # 重要なセキュリティ考慮事項
    print("  [セキュリティ考慮事項]")
    print("  - スコープは最小限に設定する（例: calendar.read、calendar.events.write）")
    print("  - トークンの有効期限を短く設定する")
    print("  - リフレッシュトークンは安全に保管する")
    print("  - ユーザーの同意は明示的に取得する")


def demo_iam_integration():
    """AWS IAM を使用した AgentCore Runtime のアクセス制御"""

    print("\n" + "─" * 70)
    print("  デモ 3: IAM + AgentCore Runtime 統合")
    print("─" * 70)

    # IAM ポリシーの例
    iam_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowInvokeAgent",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeAgent",
                    "bedrock-agentcore:InvokeAgentWithResponseStream"
                ],
                "Resource": "arn:aws:bedrock-agentcore:us-east-1:123456789012:agent/customer-support-agent"
            },
            {
                "Sid": "DenyHighRiskTools",
                "Effect": "Deny",
                "Action": "bedrock-agentcore:InvokeAgent",
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "bedrock-agentcore:ToolName": [
                            "delete_customer_data",
                            "modify_billing_plan"
                        ]
                    }
                }
            }
        ]
    }

    print("  [IAM ポリシー例: エージェント呼び出し権限の制御]")
    print(f"  {json.dumps(iam_policy, indent=4, ensure_ascii=False)}")

    # 実行ロールの例
    print("""
    [AgentCore Runtime 実行ロール]
    - エージェントは IAM 実行ロールを引き受けて AWS リソースにアクセス
    - 最小権限の原則: 必要な AWS サービスへのアクセスのみ許可
    - 例: Bedrock InvokeModel + DynamoDB Read + S3 GetObject
    """)


def run_identity_demo():
    """AgentCore Identity デモの全体実行"""

    demo_identity_overview()
    demo_oauth_2lo()
    demo_oauth_3lo()
    demo_iam_integration()

    print("\n" + "=" * 70)
    print(" AgentCore Identity デモ完了")
    print("=" * 70)
    print("\n[Key Takeaways]")
    print("1. インバウンド認証: ユーザーがエージェントを呼び出す際の認証")
    print("2. アウトバウンド認証: エージェントがリソースにアクセスする際の認証")
    print("3. OAuth 2LO: エージェント自身のリソースアクセス（M2M）")
    print("4. OAuth 3LO: ユーザーの代理で動作（ユーザー同意が必要）")
    print("5. IAM: AWS リソースへの最小権限アクセス制御")


if __name__ == "__main__":
    run_identity_demo()
