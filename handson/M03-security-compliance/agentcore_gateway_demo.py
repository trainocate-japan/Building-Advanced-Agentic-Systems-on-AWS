"""
モジュール 3: AgentCore Gateway - 認証デモ

AgentCore Gateway に対して:
1. 有効なトークンでリクエスト → 成功
2. 無効なトークンでリクエスト → 拒否

Gateway の JWT Authorizer が Cognito トークンを検証し、
認証が通ったリクエストのみバックエンド Lambda に転送されることを確認します。

前提: agentcore_identity_setup.py を実行済みであること
"""

import json
import sys
import base64
import urllib.request
import urllib.parse
import boto3

# =============================================================================
# 設定
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


def get_2lo_token(config):
    """2LO (Client Credentials) でアクセストークンを取得"""
    client_id = config["client_id_2lo"]
    client_secret = config["client_secret_2lo"]
    scopes = " ".join(config["scopes_2lo"])

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": scopes,
    }).encode()

    req = urllib.request.Request(
        config["token_endpoint"],
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())["access_token"]


def invoke_gateway(config, token, tool_name, tool_input, label=""):
    """Gateway を呼び出し"""
    agentcore = boto3.client("bedrock-agentcore", region_name=config["region"])

    print(f"  │ 🔧 ツール: {tool_name}")
    print(f"  │ 📥 入力:  {json.dumps(tool_input, ensure_ascii=False)}")
    if token:
        print(f"  │ 🔑 トークン: {token[:30]}...（有効）")
    else:
        print(f"  │ 🔑 トークン: なし（無効）")
    print(f"  │")

    try:
        # Gateway の invoke API
        payload = json.dumps({
            "tool_name": tool_name,
            "tool_input": tool_input,
        }).encode()

        invoke_params = {
            "gatewayIdentifier": config["gateway_id"],
            "targetName": "handson-tools",
            "action": f"handson-tools___{tool_name}",
            "payload": payload,
        }
        if token:
            invoke_params["authorizationToken"] = f"Bearer {token}"

        response = agentcore.invoke_gateway(**invoke_params)

        # レスポンス処理
        response_body = response.get("body", b"")
        if hasattr(response_body, "read"):
            response_body = response_body.read()
        if isinstance(response_body, bytes):
            response_body = response_body.decode()

        result = json.loads(response_body) if response_body else {}
        print(f"  │ ✅ 成功! レスポンス:")
        print(f"  │    {json.dumps(result, ensure_ascii=False, indent=2)[:200]}")
        return True

    except Exception as e:
        error_msg = str(e)
        if "AccessDenied" in error_msg or "Unauthorized" in error_msg or "403" in error_msg:
            print(f"  │ 🚫 アクセス拒否!")
            print(f"  │    {error_msg[:150]}")
        else:
            print(f"  │ ❌ エラー: {error_msg[:150]}")
        return False


# =============================================================================
# メイン
# =============================================================================

def main():
    config = load_config()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  AgentCore Gateway: 認証 (Identity) デモ                            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  Gateway の JWT Authorizer が認証を検証する様子を確認します。")
    print()
    print(f"  Gateway URL: {config['gateway_url']}")
    print(f"  Gateway ID:  {config['gateway_id']}")
    print()

    # ─── テスト 1: 有効なトークンでリクエスト ───────────────────────────────

    print("  ┌─ テスト 1: 有効なトークンでリクエスト ────────────────────────────")
    print(f"  │")
    print(f"  │ 2LO (Client Credentials) でトークンを取得してリクエストします。")
    print(f"  │")

    try:
        token = get_2lo_token(config)
        print(f"  │ ✅ トークン取得成功")
        print(f"  │")
        result = invoke_gateway(config, token, "get_order_status", {"order_id": "ORD-12345"})
    except Exception as e:
        print(f"  │ ❌ エラー: {e}")
        result = False

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 2: 無効なトークンでリクエスト ───────────────────────────────

    print()
    print("  ┌─ テスト 2: 無効なトークンでリクエスト ────────────────────────────")
    print(f"  │")
    print(f"  │ 偽のトークンでリクエストし、拒否されることを確認します。")
    print(f"  │")

    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlIn0.fake_signature"
    invoke_gateway(config, fake_token, "get_order_status", {"order_id": "ORD-12345"})

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 3: トークンなしでリクエスト ─────────────────────────────────

    print()
    print("  ┌─ テスト 3: トークンなしでリクエスト ──────────────────────────────")
    print(f"  │")
    print(f"  │ トークンを付けずにリクエストし、拒否されることを確認します。")
    print(f"  │")

    invoke_gateway(config, None, "get_order_status", {"order_id": "ORD-12345"})

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── まとめ ────────────────────────────────────────────────────────────

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("  [結果]")
    print("  • 有効なトークン → Gateway が認証を通し、Lambda が実行される")
    print("  • 無効なトークン → JWT Authorizer が拒否、Lambda に到達しない")
    print("  • トークンなし   → 同様に拒否")
    print()
    print("  [AgentCore Identity の役割]")
    print("  • インバウンド認証: JWT Authorizer がトークンを検証")
    print("  • Cognito の JWKS エンドポイントで署名を確認")
    print("  • allowedClients でクライアント ID を制限")
    print()


if __name__ == "__main__":
    main()
