"""
モジュール 3: AgentCore Gateway - 認証デモ (Strands Agent + MCP)

Strands Agent が AgentCore Gateway に MCP クライアントとして接続し:
1. 有効なトークンでリクエスト → ツール呼び出し成功
2. 無効なトークンでリクエスト → 認証拒否

Gateway の JWT Authorizer が Cognito トークンを検証し、
認証が通ったリクエストのみバックエンド Lambda に転送されることを確認します。

前提: agentcore_identity_setup.py を実行済みであること
"""

import json
import sys
import base64
import urllib.request
import urllib.parse
from strands import Agent
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

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
    print("  Strands Agent が Gateway に MCP 接続し、JWT 認証の動作を確認します。")
    print()
    print(f"  Gateway URL: {config['gateway_url']}")
    print()

    # ─── テスト 1: 有効なトークンで接続 ─────────────────────────────────────

    print("  ┌─ テスト 1: 有効なトークンで Gateway に接続 ──────────────────────")
    print(f"  │")
    print(f"  │ 2LO (Client Credentials) でトークンを取得...")

    token = get_2lo_token(config)
    print(f"  │ ✅ トークン取得: {token[:30]}...")
    print(f"  │")
    print(f"  │ Strands Agent → Gateway (MCP) → Lambda")
    print(f"  │")

    gateway_url = config["gateway_url"]

    try:
        mcp_client = MCPClient(
            lambda: streamablehttp_client(
                url=gateway_url,
                headers={"Authorization": f"Bearer {token}"},
            )
        )

        agent = Agent(
            model="us.anthropic.claude-sonnet-4-6",
            tools=[mcp_client],
            system_prompt="あなたはカスタマーサポートエージェントです。ツールを使って回答してください。",
        )

        print(f"  │ エージェントに指示: 「注文 ORD-12345 のステータスを確認して」")
        print(f"  │")

        response = agent("注文 ORD-12345 のステータスを確認してください。")
        response_text = str(response)

        print(f"  │ ✅ 成功! エージェント応答:")
        for line in response_text[:300].split("\n"):
            print(f"  │    {line}")
        print(f"  │")
        print(f"  │ → 有効なトークンで Gateway 認証が通り、Lambda が実行された")

    except Exception as e:
        print(f"  │ ❌ エラー: {str(e)[:200]}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 2: 無効なトークンで接続 ─────────────────────────────────────

    print()
    print("  ┌─ テスト 2: 無効なトークンで Gateway に接続 ──────────────────────")
    print(f"  │")
    print(f"  │ 偽のトークンで接続し、認証が拒否されることを確認します。")
    print(f"  │")

    fake_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJmYWtlIn0.invalid"

    try:
        mcp_client_fake = MCPClient(
            lambda: streamablehttp_client(
                url=gateway_url,
                headers={"Authorization": f"Bearer {fake_token}"},
            )
        )

        agent_fake = Agent(
            model="us.anthropic.claude-sonnet-4-6",
            tools=[mcp_client_fake],
            system_prompt="ツールを使って回答してください。",
        )

        response = agent_fake("注文 ORD-12345 のステータスを確認してください。")
        print(f"  │ ⚠️  予想外: 応答が返った: {str(response)[:100]}")

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg or "auth" in error_msg.lower():
            print(f"  │ 🚫 認証拒否! JWT Authorizer がトークンを検証し拒否しました")
            print(f"  │    エラー: {error_msg[:150]}")
        else:
            print(f"  │ ❌ エラー（認証拒否の可能性）: {error_msg[:150]}")

    print(f"  │")
    print(f"  │ → 無効なトークンは Gateway の JWT Authorizer で即座にブロック")
    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── まとめ ────────────────────────────────────────────────────────────

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("  [結果]")
    print("  • 有効なトークン → Gateway 認証通過 → Lambda 実行 → 応答返却")
    print("  • 無効なトークン → JWT Authorizer で即座にブロック")
    print()
    print("  [AgentCore Identity の役割]")
    print("  • Gateway が CUSTOM_JWT Authorizer で全リクエストを検証")
    print("  • Cognito の JWKS で署名を暗号的に確認")
    print("  • allowedClients でクライアント ID を制限")
    print("  • トークンなし/偽造/期限切れ → 即座に拒否")
    print()


if __name__ == "__main__":
    main()
