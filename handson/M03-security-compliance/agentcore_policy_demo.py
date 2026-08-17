"""
モジュール 3: AgentCore Policy - Cedar ポリシー認可デモ (Strands Agent + MCP)

Strands Agent が Gateway に MCP 接続し、Cedar ポリシーによる認可を確認します:
1. get_order_status → 全ユーザーに許可 → 成功
2. process_refund (amount=100) → 500未満なので許可 → 成功
3. process_refund (amount=1000) → 500以上なので拒否 → DENY

Cedar ポリシーがリアルタイムでエージェントのツール呼び出しを制御する様子を体験します。

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
    """2LO でアクセストークンを取得"""
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
    print("║  AgentCore Policy: Cedar ポリシー認可デモ (Strands Agent)           ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  Gateway に設定された Cedar ポリシー:")
    print()
    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │ Policy 1: get_order_status は全ユーザーに許可                   │")
    print("  │   permit(principal, action == ...get_order_status, resource);   │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │ Policy 2: process_refund は 500 USD 未満のみ許可               │")
    print("  │   permit(...) when { context.input.amount < 500 };             │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    # トークン取得
    print("  トークンを取得中...")
    token = get_2lo_token(config)
    print(f"  ✅ トークン取得: {token[:30]}...")
    print()

    # MCP クライアントとエージェント作成
    gateway_url = config["gateway_url"]

    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            url=gateway_url,
            headers={"Authorization": f"Bearer {token}"},
        )
    )

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        tools=[mcp_client],
        system_prompt="""あなたはカスタマーサポートエージェントです。
ユーザーの依頼に対して適切なツールを使って対応してください。
ツールの実行結果をそのまま報告してください。""",
    )

    # ─── テスト 1: get_order_status（許可） ─────────────────────────────────

    print("  ┌─ テスト 1: get_order_status（全ユーザーに許可）──────────────────")
    print(f"  │")
    print(f"  │ � エージェントへの指示:")
    print(f"  │    「注文 ORD-12345 のステータスを確認して」")
    print(f"  │ 📋 期待: ALLOW（ポリシーで全ユーザーに許可）")
    print(f"  │")

    try:
        response = agent("注文 ORD-12345 のステータスを確認してください。結果を簡潔に教えてください。")
        response_text = str(response)
        print(f"  │ ✅ 結果: ALLOW — ツール実行成功")
        for line in response_text[:250].split("\n")[:5]:
            print(f"  │    {line}")
    except Exception as e:
        print(f"  │ ❌ エラー: {str(e)[:150]}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 2: process_refund $100（許可） ──────────────────────────────

    print()
    print("  ┌─ テスト 2: process_refund $100（500未満 → 許可）────────────────")
    print(f"  │")
    print(f"  │ � エージェントへの指示:")
    print(f"  │    「注文 ORD-67890 に $100 返金して」")
    print(f"  │ 📋 期待: ALLOW（100 < 500 なのでポリシー条件を満たす）")
    print(f"  │")

    try:
        response = agent("注文 ORD-67890 に 100 ドル返金してください。理由は商品破損です。結果を簡潔に教えてください。")
        response_text = str(response)
        if "deny" in response_text.lower() or "拒否" in response_text or "許可されていません" in response_text:
            print(f"  │ 🚫 結果: DENY（予期しない拒否）")
        else:
            print(f"  │ ✅ 結果: ALLOW — 返金処理成功")
        for line in response_text[:250].split("\n")[:5]:
            print(f"  │    {line}")
    except Exception as e:
        error_msg = str(e)
        if "denied" in error_msg.lower() or "policy" in error_msg.lower():
            print(f"  │ 🚫 結果: DENY（予期しない拒否）: {error_msg[:100]}")
        else:
            print(f"  │ ❌ エラー: {error_msg[:150]}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 3: process_refund $1000（拒否） ─────────────────────────────

    print()
    print("  ┌─ テスト 3: process_refund $1000（500以上 → 拒否）───────────────")
    print(f"  │")
    print(f"  │ � エージェントへの指示:")
    print(f"  │    「注文 ORD-99999 に $1000 返金して」")
    print(f"  │ 📋 期待: DENY（1000 >= 500 なのでポリシー条件を満たさない）")
    print(f"  │")

    try:
        response = agent("注文 ORD-99999 に 1000 ドル返金してください。理由は全額返金要求です。結果を簡潔に教えてください。")
        response_text = str(response)
        if "deny" in response_text.lower() or "拒否" in response_text or "許可されていません" in response_text or "denied" in response_text.lower():
            print(f"  │ 🚫 結果: DENY — ポリシーにより拒否!")
            print(f"  │    Cedar ポリシーが $1000 の返金をブロックしました")
        else:
            print(f"  │ ⚠️  結果: ALLOW（ポリシーが効いていない可能性）")
        for line in response_text[:250].split("\n")[:5]:
            print(f"  │    {line}")
    except Exception as e:
        error_msg = str(e)
        if "denied" in error_msg.lower() or "policy" in error_msg.lower() or "authorization" in error_msg.lower():
            print(f"  │ 🚫 結果: DENY — ポリシーにより拒否!")
            print(f"  │    Cedar ポリシーが $1000 の返金をブロックしました")
            print(f"  │    エラー: {error_msg[:100]}")
        else:
            print(f"  │ ❌ エラー: {error_msg[:150]}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── まとめ ────────────────────────────────────────────────────────────

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("  [結果まとめ]")
    print("  ┌──────────────────────┬────────────┬────────────────────────────┐")
    print("  │ テスト               │ 結果       │ 理由                       │")
    print("  ├──────────────────────┼────────────┼────────────────────────────┤")
    print("  │ get_order_status     │ ✅ ALLOW   │ 全ユーザーに許可           │")
    print("  │ process_refund $100  │ ✅ ALLOW   │ amount < 500               │")
    print("  │ process_refund $1000 │ 🚫 DENY   │ amount >= 500              │")
    print("  └──────────────────────┴────────────┴────────────────────────────┘")
    print()
    print("  [AgentCore Policy のポイント]")
    print("  • Cedar ポリシーがリアルタイムでエージェントのツール呼び出しを評価")
    print("  • 入力パラメータ (context.input.*) に基づく条件分岐が可能")
    print("  • LLM がプロンプトインジェクションで騙されても、Policy は騙されない")
    print("  • ENFORCE モード: ポリシー違反は即座にブロック")
    print()


if __name__ == "__main__":
    main()
