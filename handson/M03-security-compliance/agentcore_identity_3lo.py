"""
モジュール 3: AgentCore Identity - 3LO (Authorization Code Flow) デモ

OAuth 2.0 Authorization Code Grant (3-Legged OAuth) を実際に実行し、
エージェントがユーザーの同意を得てリソースにアクセスする流れを体験します。

前提: agentcore_identity_setup.py を実行済みであること

フロー:
  1. エージェントがユーザーに認可 URL を提示
  2. ユーザーが Cognito Hosted UI でログイン＆同意
  3. 認可コードが Callback URL に返される（このデモではシミュレート）
  4. エージェントが認可コードでアクセストークンを取得
  5. エージェントがユーザーの代理でリソースにアクセス

ユースケース:
  - ユーザーのカレンダーに予定を追加
  - ユーザーのメールを送信
  - ユーザーの Google Drive にファイルを保存
"""

import json
import sys
import base64
import hashlib
import urllib.request
import urllib.parse
import boto3

# =============================================================================
# 設定ファイル読み込み
# =============================================================================

CONFIG_FILE = "identity_config.json"


def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  ❌ {CONFIG_FILE} が見つかりません。")
        print(f"     先に agentcore_identity_setup.py を実行してください。")
        sys.exit(1)


# =============================================================================
# メイン
# =============================================================================

def main():
    config = load_config()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  AgentCore Identity: 3LO (Authorization Code Flow) デモ             ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │ 3LO = 3-Legged OAuth (Authorization Code Grant)                │")
    print("  │                                                                 │")
    print("  │ ユーザーの同意が必要。エージェントはユーザーの代理で動作する    │")
    print("  │                                                                 │")
    print("  │  ┌──────┐    ┌───────────┐    ┌──────────────┐                │")
    print("  │  │ User │◀──▶│  Agent    │───▶│ Auth Server  │                │")
    print("  │  │      │    │           │◀───│ (Cognito)    │                │")
    print("  │  └──────┘    └───────────┘    └──────────────┘                │")
    print("  │   (2)同意     (1)認可URL提示    (3)認可コード                   │")
    print("  │               (4)トークン取得   (5)リソースアクセス             │")
    print("  │                     │                                           │")
    print("  │                     ▼                                           │")
    print("  │               ┌──────────┐                                     │")
    print("  │               │ Resource │ ← ユーザーの代理でアクセス          │")
    print("  │               │ Server   │                                     │")
    print("  │               └──────────┘                                     │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    # ─── Step 1: 認可 URL の生成 ────────────────────────────────────────────

    print("  ┌─ Step 1: 認可 URL の生成 ────────────────────────────────────────")
    print(f"  │")
    print(f"  │ エージェントがユーザーにログイン＆同意を求める URL を生成します。")
    print(f"  │")

    authorize_endpoint = config["authorize_endpoint"]
    client_id = config["client_id"]
    callback_url = config["callback_url"]
    scopes = " ".join(config["scopes_3lo"])

    authorize_url = (
        f"{authorize_endpoint}?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(callback_url, safe='')}&"
        f"scope={urllib.parse.quote(scopes, safe='')}"
    )

    print(f"  │ 📋 Authorize Endpoint: {authorize_endpoint}")
    print(f"  │ 📋 Response Type:      code")
    print(f"  │ 📋 Client ID:          {client_id}")
    print(f"  │ 📋 Redirect URI:       {callback_url}")
    print(f"  │ 📋 Scopes:             {scopes}")
    print(f"  │")
    print(f"  │ ┌─ 認可 URL（ユーザーに提示する URL）──────────────────────────")
    print(f"  │ │")
    print(f"  │ │ {authorize_url[:100]}")
    if len(authorize_url) > 100:
        print(f"  │ │ {authorize_url[100:200]}")
    if len(authorize_url) > 200:
        print(f"  │ │ {authorize_url[200:]}")
    print(f"  │ │")
    print(f"  │ └──────────────────────────────────────────────────────────────")
    print(f"  │")
    print(f"  │ 本番: ユーザーがこの URL にアクセスし、Cognito Hosted UI で")
    print(f"  │       ログイン後、スコープへのアクセスに同意します。")
    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── Step 2: ユーザー認証のシミュレート ─────────────────────────────────

    print()
    print("  ┌─ Step 2: ユーザー認証（Cognito Admin API でシミュレート）────────")
    print(f"  │")
    print(f"  │ デモのため、Cognito Admin API を使って認証をシミュレートします。")
    print(f"  │ 本番では Hosted UI でユーザーがブラウザからログイン＆同意します。")
    print(f"  │")
    print(f"  │ 📋 Username: {config['username']}")
    print(f"  │ 📋 Password: {config['password']}")
    print(f"  │")

    cognito_client = boto3.client("cognito-idp", region_name=config["region"])

    # Admin Initiate Auth でユーザーを認証
    try:
        # Cognito の SECRET_HASH 計算
        import hmac
        msg = config["username"] + client_id
        secret_hash = base64.b64encode(
            hmac.new(
                config["client_secret"].encode(),
                msg.encode(),
                hashlib.sha256
            ).digest()
        ).decode()

        auth_response = cognito_client.admin_initiate_auth(
            UserPoolId=config["user_pool_id"],
            ClientId=client_id,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": config["username"],
                "PASSWORD": config["password"],
                "SECRET_HASH": secret_hash,
            },
        )

        id_token = auth_response["AuthenticationResult"]["IdToken"]
        access_token = auth_response["AuthenticationResult"]["AccessToken"]
        refresh_token = auth_response["AuthenticationResult"].get("RefreshToken", "N/A")
        token_type = auth_response["AuthenticationResult"].get("TokenType", "Bearer")
        expires_in = auth_response["AuthenticationResult"].get("ExpiresIn", 3600)

        print(f"  │ ✅ ユーザー認証成功!")
        print(f"  │")
        print(f"  │ 📋 token_type: {token_type}")
        print(f"  │ 📋 expires_in: {expires_in} 秒")
        print(f"  │ 📋 id_token:   {id_token[:50]}...（省略）")
        print(f"  │ 📋 access_token: {access_token[:50]}...（省略）")

    except Exception as e:
        print(f"  │ ❌ 認証失敗: {e}")
        print(f"  │")
        print(f"  │ AdminInitiateAuth には ALLOW_USER_PASSWORD_AUTH が必要です。")
        print(f"  │ セットアップスクリプトを再実行してください。")
        print(f"  └──────────────────────────────────────────────────────────────────")
        return

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── Step 3: ID トークンの検証 ──────────────────────────────────────────

    print()
    print("  ┌─ Step 3: トークンの検証（JWT デコード）──────────────────────────")
    print(f"  │")
    print(f"  │ 3LO では ID Token にユーザー情報が含まれます。")
    print(f"  │ エージェントはこれを使って「誰の代理で動作しているか」を確認します。")
    print(f"  │")

    try:
        parts = id_token.split(".")
        if len(parts) == 3:
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload).decode())

            print(f"  │ ┌─ ID Token ペイロード ─────────────────────────────────────")
            print(f"  │ │ iss:        {decoded.get('iss', 'N/A')}")
            print(f"  │ │ sub:        {decoded.get('sub', 'N/A')}")
            print(f"  │ │ aud:        {decoded.get('aud', 'N/A')}")
            print(f"  │ │ token_use:  {decoded.get('token_use', 'N/A')}")
            print(f"  │ │ auth_time:  {decoded.get('auth_time', 'N/A')}")
            print(f"  │ │ exp:        {decoded.get('exp', 'N/A')}")
            email = decoded.get("email", "N/A")
            cognito_username = decoded.get("cognito:username", "N/A")
            print(f"  │ │ email:      {email}")
            print(f"  │ │ username:   {cognito_username}")
            print(f"  │ └──────────────────────────────────────────────────────────")
            print(f"  │")
            print(f"  │ ✅ エージェントは「{cognito_username}」の代理で動作していることを確認")
    except Exception as e:
        print(f"  │ ⚠️  JWT デコード失敗: {e}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── Step 4: Access Token でリソースアクセス ─────────────────────────────

    print()
    print("  ┌─ Step 4: Access Token でリソースアクセス（シミュレート）──────────")
    print(f"  │")
    print(f"  │ 本番ではこのトークンを使って外部サービスの API を呼び出します。")
    print(f"  │")
    print(f"  │ 例:")
    print(f"  │   curl -H 'Authorization: Bearer <access_token>' \\")
    print(f"  │        https://api.example.com/user/calendar")
    print(f"  │")
    print(f"  │ ┌─ AgentCore でのフロー ────────────────────────────────────────")
    print(f"  │ │")
    print(f"  │ │  1. ユーザーが Hosted UI でログイン＆同意")
    print(f"  │ │  2. 認可コードが AgentCore Callback URL に返される")
    print(f"  │ │  3. AgentCore が自動的にトークンを取得")
    print(f"  │ │  4. Token Vault に安全に保存")
    print(f"  │ │  5. エージェントが @requires_access_token で取得")
    print(f"  │ │  6. ユーザーの代理で外部サービスにアクセス")
    print(f"  │ │")
    print(f"  │ └──────────────────────────────────────────────────────────────")
    print(f"  │")

    # Access Token もデコード
    try:
        parts = access_token.split(".")
        if len(parts) == 3:
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload).decode())

            print(f"  │ ┌─ Access Token ペイロード ─────────────────────────────────")
            print(f"  │ │ iss:        {decoded.get('iss', 'N/A')}")
            print(f"  │ │ sub:        {decoded.get('sub', 'N/A')}")
            print(f"  │ │ token_use:  {decoded.get('token_use', 'N/A')}")
            print(f"  │ │ scope:      {decoded.get('scope', 'N/A')}")
            print(f"  │ │ client_id:  {decoded.get('client_id', 'N/A')}")
            print(f"  │ │ username:   {decoded.get('username', 'N/A')}")
            print(f"  │ └──────────────────────────────────────────────────────────")
    except Exception as e:
        print(f"  │ ⚠️  Access Token デコード失敗: {e}")

    print(f"  │")
    print(f"  │ ✅ ユーザーの同意に基づき、アクセストークンを取得できた")
    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── 2LO vs 3LO 比較 ──────────────────────────────────────────────────

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("  [2LO vs 3LO 比較]")
    print()
    print("  ┌────────────────┬────────────────────────┬────────────────────────┐")
    print("  │                │ 2LO (Client Creds)     │ 3LO (Auth Code)        │")
    print("  ├────────────────┼────────────────────────┼────────────────────────┤")
    print("  │ ユーザー同意   │ 不要                   │ 必須                   │")
    print("  │ トークン主体   │ アプリケーション自身   │ ユーザー               │")
    print("  │ ID Token       │ なし                   │ あり（ユーザー情報）   │")
    print("  │ スコープ       │ カスタムスコープのみ   │ openid/profile/email   │")
    print("  │ ユースケース   │ M2M、バッチ処理       │ ユーザー代理動作       │")
    print("  │ セキュリティ   │ Client Secret 管理     │ + ユーザー同意管理    │")
    print("  └────────────────┴────────────────────────┴────────────────────────┘")
    print()
    print("  [3LO のポイント]")
    print("  • ユーザーの明示的な同意が必要（スコープごとに許可）")
    print("  • ID Token でユーザーの身元を確認できる")
    print("  • AgentCore の Token Vault がトークンのライフサイクルを管理")
    print("  • リフレッシュトークンで自動更新が可能")
    print()
    print("  [AgentCore での活用例]")
    print("  • ユーザーのカレンダーに予定を追加するエージェント")
    print("  • ユーザーの Slack にメッセージを送信するエージェント")
    print("  • ユーザーの GitHub リポジトリを操作するエージェント")
    print()


if __name__ == "__main__":
    main()
