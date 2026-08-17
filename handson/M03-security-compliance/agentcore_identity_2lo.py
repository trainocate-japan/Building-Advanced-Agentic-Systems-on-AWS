"""
モジュール 3: AgentCore Identity - 2LO (Client Credentials Flow) デモ

OAuth 2.0 Client Credentials Grant (2-Legged OAuth) を実際に実行し、
エージェントがユーザーの介在なしにサービス間でトークンを取得する流れを体験します。

前提: agentcore_identity_setup.py を実行済みであること

フロー:
  1. エージェント（Client）が Client ID + Secret でトークンエンドポイントにリクエスト
  2. 認可サーバー（Cognito）がアクセストークンを発行
  3. エージェントがトークンを使ってリソースにアクセス

ユースケース:
  - エージェントが内部 DB にアクセス
  - バッチ処理エージェントが外部 API にアクセス
  - M2M (Machine-to-Machine) 通信
"""

import json
import sys
import base64
import urllib.request
import urllib.parse

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
    print("║  AgentCore Identity: 2LO (Client Credentials Flow) デモ             ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │ 2LO = 2-Legged OAuth (Client Credentials Grant)               │")
    print("  │                                                                 │")
    print("  │ ユーザーの介在なし。エージェント自身の権限でリソースにアクセス  │")
    print("  │                                                                 │")
    print("  │  ┌───────────┐        ┌──────────────────┐                    │")
    print("  │  │  Agent    │─(1)──▶ │ Token Endpoint   │                    │")
    print("  │  │ (Client)  │◀─(2)── │ (Cognito)        │                    │")
    print("  │  └───────────┘        └──────────────────┘                    │")
    print("  │       │                                                         │")
    print("  │       │ (3) アクセストークンでリソースアクセス                  │")
    print("  │       ▼                                                         │")
    print("  │  ┌──────────┐                                                  │")
    print("  │  │ Resource │                                                  │")
    print("  │  │ Server   │                                                  │")
    print("  │  └──────────┘                                                  │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    # ─── Step 1: Client Credentials でトークン取得 ──────────────────────────

    print("  ┌─ Step 1: トークンリクエスト送信 ─────────────────────────────────")
    print(f"  │")
    print(f"  │ Token Endpoint: {config['token_endpoint']}")
    print(f"  │ Grant Type:     client_credentials")
    print(f"  │ Scopes:         {', '.join(config['scopes_2lo'])}")
    print(f"  │ Client ID:      {config['client_id_2lo']}")
    print(f"  │")
    print(f"  │ リクエスト送信中...")

    # HTTP POST でトークン取得
    token_endpoint = config["token_endpoint"]
    client_id = config["client_id_2lo"]
    client_secret = config["client_secret_2lo"]
    scopes = " ".join(config["scopes_2lo"])

    # Basic 認証ヘッダー
    credentials = base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": scopes,
    }).encode()

    req = urllib.request.Request(
        token_endpoint,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            token_response = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  │")
        print(f"  │ ❌ トークン取得失敗: HTTP {e.code}")
        print(f"  │    {error_body}")
        print(f"  └──────────────────────────────────────────────────────────────────")
        return

    print(f"  │")
    print(f"  │ ✅ トークン取得成功!")
    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── Step 2: トークンの中身を確認 ──────────────────────────────────────

    access_token = token_response.get("access_token", "")
    token_type = token_response.get("token_type", "")
    expires_in = token_response.get("expires_in", 0)

    print()
    print("  ┌─ Step 2: レスポンス確認 ─────────────────────────────────────────")
    print(f"  │")
    print(f"  │ 📋 token_type: {token_type}")
    print(f"  │ 📋 expires_in: {expires_in} 秒")
    print(f"  │ 📋 scope:      {token_response.get('scope', 'N/A')}")
    print(f"  │ 📋 access_token: {access_token[:50]}...（省略）")
    print(f"  │")

    # JWT デコード（署名検証なし、構造確認のみ）
    try:
        parts = access_token.split(".")
        if len(parts) == 3:
            # JWT ペイロードをデコード
            payload = parts[1]
            # パディング追加
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload).decode())

            print(f"  │ ┌─ JWT ペイロード（デコード済み）──────────────────────────")
            print(f"  │ │ iss:    {decoded.get('iss', 'N/A')}")
            print(f"  │ │ sub:    {decoded.get('sub', 'N/A')}")
            print(f"  │ │ scope:  {decoded.get('scope', 'N/A')}")
            print(f"  │ │ exp:    {decoded.get('exp', 'N/A')}")
            print(f"  │ │ iat:    {decoded.get('iat', 'N/A')}")
            print(f"  │ │ client_id: {decoded.get('client_id', 'N/A')}")
            print(f"  │ │ token_use: {decoded.get('token_use', 'N/A')}")
            print(f"  │ └──────────────────────────────────────────────────────────")
    except Exception as e:
        print(f"  │ ⚠️  JWT デコード失敗: {e}")

    print(f"  │")
    print(f"  │ ✅ ユーザーの介在なしでトークンを取得できた")
    print(f"  │    → エージェントはこのトークンでリソースサーバーにアクセス可能")
    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── まとめ ────────────────────────────────────────────────────────────

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("  [2LO のポイント]")
    print("  • ユーザーの同意・ログインが不要（M2M 通信）")
    print("  • Client ID + Secret のみでトークンを取得")
    print("  • カスタムスコープ（Resource Server）が必要")
    print("  • openid/profile/email スコープは使用不可")
    print()
    print("  [AgentCore での活用例]")
    print("  • エージェントが内部 API にアクセスする際のサービス認証")
    print("  • バッチ処理エージェントの外部サービスアクセス")
    print("  • エージェント間通信の認証")
    print()


if __name__ == "__main__":
    main()
