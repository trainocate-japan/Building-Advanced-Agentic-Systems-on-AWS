"""
モジュール 3: AgentCore Identity - 前準備セットアップ

以下のリソースを作成し、2LO/3LO デモの前提環境を構築します:
1. Amazon Cognito User Pool（OAuth 2.0 認可サーバー）
2. Resource Server + カスタムスコープ（2LO 用）
3. App Client（client_credentials + code フロー両方対応）
4. テストユーザー
5. AgentCore OAuth2 Credential Provider
6. Callback URL の Cognito への登録

設定情報は identity_config.json に保存され、後続の 2LO/3LO デモで使用されます。
"""

import boto3
import json
import random
import string

# =============================================================================
# 設定
# =============================================================================

REGION = "us-east-1"
POOL_NAME = "AgentCoreIdentityHandsonPool"
CLIENT_NAME = "AgentCoreHandsonClient"
CREDENTIAL_PROVIDER_NAME = "AgentCoreHandsonProvider"
RESOURCE_SERVER_ID = "agentcore-demo-api"
RESOURCE_SERVER_NAME = "AgentCore Demo API"
CONFIG_FILE = "identity_config.json"


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


def print_end():
    print(f"  └──────────────────────────────────────────────────────────────────")


def random_suffix(length=5):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


# =============================================================================
# セットアップ
# =============================================================================

def main():
    print_header("AgentCore Identity セットアップ")

    print("  以下のリソースを作成します:")
    print("    1. Cognito User Pool + ドメイン")
    print("    2. Resource Server（2LO 用カスタムスコープ）")
    print("    3. App Client（client_credentials + code 対応）")
    print("    4. テストユーザー")
    print("    5. AgentCore OAuth2 Credential Provider")
    print("    6. Callback URL 登録")
    print()
    print(f"  設定は {CONFIG_FILE} に保存されます")
    print()

    cognito_client = boto3.client("cognito-idp", region_name=REGION)
    agentcore_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    # ─── Step 1: User Pool + ドメイン ───────────────────────────────────────

    print_step(1, "Cognito User Pool + ドメイン作成")

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
    print_success("User Pool 作成完了")
    print_info("User Pool ID", user_pool_id)

    domain_name = f"agentcore-handson-{random_suffix()}"
    cognito_client.create_user_pool_domain(
        Domain=domain_name,
        UserPoolId=user_pool_id,
    )
    print_success(f"ドメイン作成完了: {domain_name}")
    print_end()

    # ─── Step 2: Resource Server（2LO 用） ──────────────────────────────────

    print_step(2, "Resource Server 作成（2LO 用カスタムスコープ）")

    cognito_client.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=RESOURCE_SERVER_ID,
        Name=RESOURCE_SERVER_NAME,
        Scopes=[
            {"ScopeName": "read", "ScopeDescription": "リソース読み取り"},
            {"ScopeName": "write", "ScopeDescription": "リソース書き込み"},
        ],
    )
    print_success("Resource Server 作成完了")
    print_info("Identifier", RESOURCE_SERVER_ID)
    print_info("Scopes", f"{RESOURCE_SERVER_ID}/read, {RESOURCE_SERVER_ID}/write")
    print(f"  │")
    print(f"  │ ※ 2LO (Client Credentials) では Resource Server のカスタムスコープが必要です")
    print(f"  │   Cognito の openid/profile/email スコープは 2LO では使用できません")
    print_end()

    # ─── Step 3: App Client ─────────────────────────────────────────────────

    print_step(3, "App Client 作成（2LO + 3LO 両対応）")

    client_response = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=CLIENT_NAME,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials", "code"],
        AllowedOAuthScopes=[
            "openid", "profile", "email",                   # 3LO 用
            f"{RESOURCE_SERVER_ID}/read",                    # 2LO 用
            f"{RESOURCE_SERVER_ID}/write",                   # 2LO 用
        ],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        CallbackURLs=["https://localhost/callback"],  # 仮（後で AgentCore の URL に更新）
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
        ],
    )
    client_id = client_response["UserPoolClient"]["ClientId"]
    client_secret = client_response["UserPoolClient"]["ClientSecret"]
    print_success("App Client 作成完了")
    print_info("Client ID", client_id)
    print_info("Client Secret", f"{client_secret[:10]}...（省略）")
    print_info("OAuth Flows", "client_credentials (2LO) + code (3LO)")
    print_end()

    # ─── Step 4: テストユーザー ─────────────────────────────────────────────

    print_step(4, "テストユーザー作成（3LO の同意フロー用）")

    username = f"testuser-{random_suffix()}"
    password = f"TestPass{random_suffix(6)}!1"

    cognito_client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        TemporaryPassword=password,
        MessageAction="SUPPRESS",
        UserAttributes=[
            {"Name": "email", "Value": f"{username}@example.com"},
            {"Name": "email_verified", "Value": "true"},
        ],
    )
    cognito_client.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=username,
        Password=password,
        Permanent=True,
    )
    print_success(f"テストユーザー作成完了")
    print_info("Username", username)
    print_info("Password", password)
    print_end()

    # ─── Step 5: AgentCore Credential Provider ──────────────────────────────

    print_step(5, "AgentCore OAuth2 Credential Provider 作成")

    issuer_url = (
        f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}"
        f"/.well-known/openid-configuration"
    )

    response = agentcore_client.create_oauth2_credential_provider(
        name=CREDENTIAL_PROVIDER_NAME,
        credentialProviderVendor="CustomOauth2",
        oauth2ProviderConfigInput={
            "customOauth2ProviderConfig": {
                "oauthDiscovery": {
                    "discoveryUrl": issuer_url
                },
                "clientId": client_id,
                "clientSecret": client_secret,
            }
        },
    )

    callback_url = response.get("callbackUrl", "N/A")
    provider_arn = response.get("credentialProviderArn", "N/A")

    print_success("Credential Provider 作成完了")
    print_info("Provider ARN", provider_arn)
    print_info("Callback URL", callback_url)
    print_info("Status", "READY")
    print_end()

    # ─── Step 6: Callback URL 登録 ──────────────────────────────────────────

    print_step(6, "Callback URL を Cognito に登録")

    cognito_client.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        ClientName=CLIENT_NAME,
        AllowedOAuthFlows=["client_credentials", "code"],
        AllowedOAuthScopes=[
            "openid", "profile", "email",
            f"{RESOURCE_SERVER_ID}/read",
            f"{RESOURCE_SERVER_ID}/write",
        ],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        CallbackURLs=[callback_url],
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
        ],
    )
    print_success("Callback URL 登録完了")
    print_info("URL", callback_url)
    print_end()

    # ─── 設定ファイル保存 ───────────────────────────────────────────────────

    hosted_ui_url = f"https://{domain_name}.auth.{REGION}.amazoncognito.com"
    token_endpoint = f"{hosted_ui_url}/oauth2/token"
    authorize_endpoint = f"{hosted_ui_url}/oauth2/authorize"

    config = {
        "region": REGION,
        "user_pool_id": user_pool_id,
        "domain_name": domain_name,
        "client_id": client_id,
        "client_secret": client_secret,
        "username": username,
        "password": password,
        "issuer_url": issuer_url,
        "hosted_ui_url": hosted_ui_url,
        "token_endpoint": token_endpoint,
        "authorize_endpoint": authorize_endpoint,
        "callback_url": callback_url,
        "provider_arn": provider_arn,
        "credential_provider_name": CREDENTIAL_PROVIDER_NAME,
        "resource_server_id": RESOURCE_SERVER_ID,
        "scopes_2lo": [f"{RESOURCE_SERVER_ID}/read", f"{RESOURCE_SERVER_ID}/write"],
        "scopes_3lo": ["openid", "profile", "email"],
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print()
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"  📁 設定を {CONFIG_FILE} に保存しました")
    print()
    print(f"  次のステップ:")
    print(f"    • 2LO デモ: python agentcore_identity_2lo.py")
    print(f"    • 3LO デモ: python agentcore_identity_3lo.py")
    print()

    print_header("セットアップ完了")


if __name__ == "__main__":
    main()
