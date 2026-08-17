"""
モジュール 3: AgentCore Identity - 認証と認可の実装デモ

実際に以下のリソースを作成し、AgentCore Identity の認証フローを体験します:
1. Amazon Cognito User Pool（OAuth 2.0 認可サーバー）
2. AgentCore OAuth2 Credential Provider（エージェントの認証情報管理）
3. Callback URL の Cognito への登録

実行後、作成したリソースの確認と、クリーンアップを行います。
"""

import boto3
import json
import time
import random
import string
import sys

# =============================================================================
# 設定
# =============================================================================

REGION = "us-east-1"
POOL_NAME = "AgentCoreIdentityHandsonPool"
CLIENT_NAME = "AgentCoreHandsonClient"
CREDENTIAL_PROVIDER_NAME = "AgentCoreHandsonProvider"


# =============================================================================
# ヘルパー関数
# =============================================================================

def print_header(title):
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print(f"║  {title:<66} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()


def print_step(step_num, title):
    print()
    print(f"  ┌─ Step {step_num} ──────────────────────────────────────────────────────")
    print(f"  │ {title}")
    print(f"  │")


def print_info(key, value):
    print(f"  │ 📋 {key}: {value}")


def print_success(message):
    print(f"  │ ✅ {message}")


def print_error(message):
    print(f"  │ ❌ {message}")


def print_end():
    print(f"  └──────────────────────────────────────────────────────────────────")


def random_suffix(length=5):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


# =============================================================================
# Step 1: Cognito User Pool の作成
# =============================================================================

def create_cognito_user_pool(cognito_client):
    """Cognito User Pool、ドメイン、クライアント、テストユーザーを作成"""

    print_step(1, "Amazon Cognito User Pool の作成（OAuth 2.0 認可サーバー）")

    # User Pool 作成
    print_info("アクション", "User Pool を作成中...")
    response = cognito_client.create_user_pool(
        PoolName=POOL_NAME,
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": True,
                "RequireLowercase": True,
                "RequireNumbers": True,
                "RequireSymbols": False,
            }
        },
        AutoVerifiedAttributes=["email"],
        Schema=[
            {
                "Name": "email",
                "AttributeDataType": "String",
                "Required": True,
                "Mutable": True,
            }
        ],
    )
    user_pool_id = response["UserPool"]["Id"]
    print_success(f"User Pool 作成完了")
    print_info("User Pool ID", user_pool_id)

    # ドメイン作成
    domain_name = f"agentcore-handson-{random_suffix()}"
    print_info("アクション", f"ドメイン '{domain_name}' を作成中...")
    cognito_client.create_user_pool_domain(
        Domain=domain_name,
        UserPoolId=user_pool_id,
    )
    print_success(f"ドメイン作成完了")

    # クライアント作成（シークレットあり + Hosted UI）
    print_info("アクション", "App Client を作成中...")
    client_response = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=CLIENT_NAME,
        GenerateSecret=True,
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "profile", "email"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        CallbackURLs=["https://localhost/callback"],  # 仮の callback URL（後で更新）
    )
    client_id = client_response["UserPoolClient"]["ClientId"]
    client_secret = client_response["UserPoolClient"]["ClientSecret"]
    print_success(f"App Client 作成完了")
    print_info("Client ID", client_id)
    print_info("Client Secret", f"{client_secret[:10]}...（セキュリティのため省略）")

    # テストユーザー作成
    username = f"testuser-{random_suffix()}"
    password = f"Test{random_suffix(8)}!1"
    print_info("アクション", f"テストユーザー '{username}' を作成中...")
    cognito_client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=password,
        MessageAction="SUPPRESS",
    )
    cognito_client.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=username,
        Password=password,
        Permanent=True,
    )
    print_success(f"テストユーザー作成完了")
    print_info("Username", username)

    # Issuer URL の構築
    issuer_url = (
        f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}"
        f"/.well-known/openid-configuration"
    )
    hosted_ui_url = f"https://{domain_name}.auth.{REGION}.amazoncognito.com"

    print(f"  │")
    print(f"  │ ┌─ 作成された認可サーバー情報 ────────────────────────────────")
    print(f"  │ │ Issuer URL:    {issuer_url}")
    print(f"  │ │ Hosted UI URL: {hosted_ui_url}")
    print(f"  │ │ Grant Type:    authorization_code (3LO)")
    print(f"  │ │ Scopes:        openid, profile, email")
    print(f"  │ └──────────────────────────────────────────────────────────────")
    print_end()

    return {
        "user_pool_id": user_pool_id,
        "domain_name": domain_name,
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
        "issuer_url": issuer_url,
        "hosted_ui_url": hosted_ui_url,
    }


# =============================================================================
# Step 2: AgentCore OAuth2 Credential Provider の作成
# =============================================================================

def create_credential_provider(agentcore_client, cognito_info):
    """AgentCore の OAuth2 Credential Provider を作成"""

    print_step(2, "AgentCore OAuth2 Credential Provider の作成")

    print(f"  │ Credential Provider は AgentCore Identity の中核コンポーネントです。")
    print(f"  │ エージェントが外部サービスにアクセスする際の認証情報を管理します。")
    print(f"  │")

    print_info("アクション", "Credential Provider を作成中...")
    print_info("Provider Name", CREDENTIAL_PROVIDER_NAME)
    print_info("Vendor", "CustomOauth2")
    print_info("Discovery URL", cognito_info["issuer_url"])

    response = agentcore_client.create_oauth2_credential_provider(
        name=CREDENTIAL_PROVIDER_NAME,
        credentialProviderVendor="CustomOauth2",
        oauth2ProviderConfigInput={
            "customOauth2ProviderConfig": {
                "oauthDiscovery": {
                    "discoveryUrl": cognito_info["issuer_url"]
                },
                "clientId": cognito_info["client_id"],
                "clientSecret": cognito_info["client_secret"],
            }
        },
    )

    callback_url = response.get("callbackUrl", "N/A")
    provider_arn = response.get("credentialProviderArn", "N/A")

    print(f"  │")
    print_success("Credential Provider 作成完了!")
    print_info("Provider ARN", provider_arn)
    print_info("Callback URL", callback_url)
    print(f"  │")
    print(f"  │ ┌─ AgentCore Identity フロー ──────────────────────────────────")
    print(f"  │ │")
    print(f"  │ │  [ユーザー] ──認証──▶ [Cognito] ──トークン──▶ [AgentCore]")
    print(f"  │ │                                                    │")
    print(f"  │ │                                              Token Vault に保存")
    print(f"  │ │                                                    │")
    print(f"  │ │  [エージェント] ◀──アクセストークン取得──────────────┘")
    print(f"  │ │        │")
    print(f"  │ │        └──▶ [外部サービス] にユーザーの代理でアクセス")
    print(f"  │ │")
    print(f"  │ └──────────────────────────────────────────────────────────────")
    print_end()

    return {
        "callback_url": callback_url,
        "provider_arn": provider_arn,
    }


# =============================================================================
# Step 3: Callback URL を Cognito に登録
# =============================================================================

def register_callback_url(cognito_client, cognito_info, provider_info):
    """AgentCore から取得した Callback URL を Cognito クライアントに登録"""

    print_step(3, "Callback URL を Cognito に登録")

    print(f"  │ AgentCore が発行した Callback URL を Cognito App Client に登録します。")
    print(f"  │ これにより OAuth 2.0 Authorization Code Flow が完成します。")
    print(f"  │")

    callback_url = provider_info["callback_url"]
    print_info("Callback URL", callback_url)
    print_info("アクション", "Cognito App Client を更新中...")

    cognito_client.update_user_pool_client(
        UserPoolId=cognito_info["user_pool_id"],
        ClientId=cognito_info["client_id"],
        ClientName=CLIENT_NAME,
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "profile", "email"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        CallbackURLs=[callback_url],
    )

    print_success("Callback URL 登録完了!")
    print(f"  │")
    print(f"  │ これで OAuth 2.0 Authorization Code Flow (3LO) の準備が整いました:")
    print(f"  │   1. ユーザーが Cognito Hosted UI でログイン")
    print(f"  │   2. 認可コードが Callback URL に返される")
    print(f"  │   3. AgentCore がトークンを取得し Token Vault に保存")
    print(f"  │   4. エージェントがユーザーの代理で外部サービスにアクセス")
    print_end()


# =============================================================================
# Step 4: 作成したリソースの確認
# =============================================================================

def verify_resources(agentcore_client, cognito_client, cognito_info):
    """作成したリソースを API で確認"""

    print_step(4, "作成したリソースの確認")

    # Credential Provider の確認
    print_info("アクション", "Credential Provider を取得中...")
    response = agentcore_client.get_oauth2_credential_provider(
        name=CREDENTIAL_PROVIDER_NAME
    )
    print_success("Credential Provider 確認OK")
    print_info("Name", response.get("name"))
    print_info("Status", response.get("status", "N/A"))
    print_info("Vendor", response.get("credentialProviderVendor"))
    print_info("ARN", response.get("credentialProviderArn", "N/A"))

    print(f"  │")

    # 一覧表示
    print_info("アクション", "全 Credential Provider を一覧表示...")
    list_response = agentcore_client.list_oauth2_credential_providers()
    providers = list_response.get("credentialProviders", [])
    print_success(f"{len(providers)} 個の Credential Provider が存在")
    for p in providers:
        print(f"  │   - {p.get('name')} (vendor: {p.get('credentialProviderVendor')})")

    print(f"  │")

    # Cognito User Pool の確認
    print_info("アクション", "Cognito User Pool を確認中...")
    pool_response = cognito_client.describe_user_pool(
        UserPoolId=cognito_info["user_pool_id"]
    )
    pool_name = pool_response["UserPool"].get("Name", "N/A")
    pool_id = pool_response["UserPool"].get("Id", "N/A")
    print_success(f"User Pool 確認OK: {pool_name} ({pool_id})")

    print_end()


# =============================================================================
# Step 5: クリーンアップ
# =============================================================================

def cleanup(agentcore_client, cognito_client, cognito_info):
    """作成したリソースを削除"""

    print_step(5, "クリーンアップ（リソース削除）")

    # Credential Provider 削除
    print_info("アクション", "Credential Provider を削除中...")
    try:
        agentcore_client.delete_oauth2_credential_provider(
            name=CREDENTIAL_PROVIDER_NAME
        )
        print_success("Credential Provider 削除完了")
    except Exception as e:
        print_error(f"Credential Provider 削除失敗: {e}")

    # Cognito ドメイン削除
    print_info("アクション", "Cognito ドメインを削除中...")
    try:
        cognito_client.delete_user_pool_domain(
            Domain=cognito_info["domain_name"],
            UserPoolId=cognito_info["user_pool_id"],
        )
        print_success("ドメイン削除完了")
    except Exception as e:
        print_error(f"ドメイン削除失敗: {e}")

    # Cognito User Pool 削除（クライアントとユーザーも一緒に削除される）
    print_info("アクション", "Cognito User Pool を削除中...")
    try:
        cognito_client.delete_user_pool(UserPoolId=cognito_info["user_pool_id"])
        print_success("User Pool 削除完了（クライアント・ユーザーも同時に削除）")
    except Exception as e:
        print_error(f"User Pool 削除失敗: {e}")

    print_end()


# =============================================================================
# アーキテクチャ解説
# =============================================================================

def show_architecture():
    """AgentCore Identity の全体アーキテクチャを表示"""

    print_header("AgentCore Identity アーキテクチャ解説")

    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │              AgentCore Identity 認証フロー                       │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │                                                                  │")
    print("  │  [インバウンド認証] ユーザー → AgentCore Runtime                │")
    print("  │    ├── AWS IAM Sig V4                                           │")
    print("  │    └── OAuth Token                                              │")
    print("  │                                                                  │")
    print("  │  [アウトバウンド認証] AgentCore Runtime → ツール/リソース       │")
    print("  │    ├── IAM Role → AWS リソース                                  │")
    print("  │    └── OAuth Token → 外部サービス（今回のデモ）                 │")
    print("  │                                                                  │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │  OAuth フロー種別                                                │")
    print("  │  ┌──────────┬──────────────────────────────────────────┐       │")
    print("  │  │ 2LO      │ Client Credentials: エージェント自身の    │       │")
    print("  │  │ (2-Leg)  │ リソースアクセス（M2M、ユーザー不要）    │       │")
    print("  │  ├──────────┼──────────────────────────────────────────┤       │")
    print("  │  │ 3LO      │ Authorization Code: ユーザーの代理で      │       │")
    print("  │  │ (3-Leg)  │ 動作（ユーザー同意が必要）← 今回のデモ  │       │")
    print("  │  └──────────┴──────────────────────────────────────────┘       │")
    print("  │                                                                  │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │  AgentCore Gateway のターゲット別認証                            │")
    print("  │  ┌──────────────┬────────────────┬────────────────────┐       │")
    print("  │  │ ターゲット   │ 認証方式       │ ユースケース       │       │")
    print("  │  ├──────────────┼────────────────┼────────────────────┤       │")
    print("  │  │ AWS Lambda   │ IAM            │ 内部ツール         │       │")
    print("  │  │ MCP サーバー │ OAuth Token    │ 外部 MCP ツール    │       │")
    print("  │  │ OpenAPI      │ IAM            │ REST API           │       │")
    print("  │  │ Smithy       │ IAM            │ AWS スタイル API   │       │")
    print("  │  └──────────────┴────────────────┴────────────────────┘       │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()


# =============================================================================
# メイン実行
# =============================================================================

def main():
    print_header("AgentCore Identity デモ: Cognito + Credential Provider")

    print("  このデモでは以下を実際に作成・実行します:")
    print("    1. Cognito User Pool（OAuth 2.0 認可サーバー）")
    print("    2. AgentCore OAuth2 Credential Provider")
    print("    3. Callback URL の登録")
    print("    4. リソースの確認")
    print("    5. クリーンアップ")
    print()

    # クライアント初期化
    cognito_client = boto3.client("cognito-idp", region_name=REGION)
    agentcore_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    cognito_info = None

    try:
        # Step 1: Cognito User Pool 作成
        cognito_info = create_cognito_user_pool(cognito_client)

        # Step 2: AgentCore Credential Provider 作成
        provider_info = create_credential_provider(agentcore_client, cognito_info)

        # Step 3: Callback URL を Cognito に登録
        register_callback_url(cognito_client, cognito_info, provider_info)

        # Step 4: リソース確認
        verify_resources(agentcore_client, cognito_client, cognito_info)

        # アーキテクチャ解説
        show_architecture()

    except Exception as e:
        print()
        print(f"  ❌ エラーが発生しました: {e}")
        print()
        import traceback
        traceback.print_exc()

    finally:
        # Step 5: クリーンアップ
        if cognito_info:
            cleanup(agentcore_client, cognito_client, cognito_info)

    print_header("デモ完了")
    print("  [Key Takeaways]")
    print("  1. Cognito User Pool が OAuth 2.0 認可サーバーとして機能")
    print("  2. AgentCore Credential Provider が認証情報を一元管理")
    print("  3. Callback URL で OAuth フローが完結")
    print("  4. エージェントは Token Vault からトークンを取得して外部サービスにアクセス")
    print("  5. インバウンド（ユーザー→エージェント）とアウトバウンド（エージェント→サービス）の分離")
    print()


if __name__ == "__main__":
    main()
