"""
モジュール 3: AgentCore Policy - Cedar ポリシー認可デモ

Gateway + Policy Engine に設定された Cedar ポリシーによる認可を確認します:
1. get_order_status → 全ユーザーに許可 → 成功
2. process_refund (amount=100) → 500未満なので許可 → 成功
3. process_refund (amount=1000) → 500以上なので拒否 → DENY

Cedar ポリシーがリアルタイムでツール呼び出しを制御する様子を体験します。

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


def invoke_gateway_tool(config, token, tool_name, tool_input):
    """Gateway 経由でツールを呼び出し、結果を返す"""
    agentcore = boto3.client("bedrock-agentcore", region_name=config["region"])

    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": tool_input,
    }).encode()

    try:
        response = agentcore.invoke_gateway(
            gatewayIdentifier=config["gateway_id"],
            targetName="handson-tools",
            action=f"handson-tools___{tool_name}",
            payload=payload,
            authorizationToken=f"Bearer {token}",
        )

        response_body = response.get("body", b"")
        if hasattr(response_body, "read"):
            response_body = response_body.read()
        if isinstance(response_body, bytes):
            response_body = response_body.decode()

        return {"success": True, "body": json.loads(response_body) if response_body else {}}

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# メイン
# =============================================================================

def main():
    config = load_config()

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  AgentCore Policy: Cedar ポリシー認可デモ                            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  Gateway に設定された Cedar ポリシー:")
    print()
    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │ Policy 1: get_order_status は全ユーザーに許可                   │")
    print("  │                                                                  │")
    print("  │   permit(                                                        │")
    print("  │     principal,                                                   │")
    print("  │     action == AgentCore::Action::\"...get_order_status\",        │")
    print("  │     resource == AgentCore::Gateway::\"<gateway-arn>\"            │")
    print("  │   );                                                             │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │ Policy 2: process_refund は 500 USD 未満のみ許可               │")
    print("  │                                                                  │")
    print("  │   permit(                                                        │")
    print("  │     principal,                                                   │")
    print("  │     action == AgentCore::Action::\"...process_refund\",          │")
    print("  │     resource == AgentCore::Gateway::\"<gateway-arn>\"            │")
    print("  │   ) when {                                                       │")
    print("  │     context.input.amount < 500                                   │")
    print("  │   };                                                             │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    # トークン取得
    print("  トークンを取得中...")
    token = get_2lo_token(config)
    print(f"  ✅ トークン取得成功: {token[:30]}...")
    print()

    # ─── テスト 1: get_order_status（許可） ─────────────────────────────────

    print("  ┌─ テスト 1: get_order_status（全ユーザーに許可）──────────────────")
    print(f"  │")
    print(f"  │ 🔧 ツール: get_order_status")
    print(f"  │ 📥 入力:  {{\"order_id\": \"ORD-12345\"}}")
    print(f"  │ 📋 期待:  ALLOW（ポリシーで全ユーザーに許可）")
    print(f"  │")

    result = invoke_gateway_tool(config, token, "get_order_status", {"order_id": "ORD-12345"})
    if result["success"]:
        print(f"  │ ✅ 結果: ALLOW — ツール実行成功")
        print(f"  │    レスポンス: {json.dumps(result['body'], ensure_ascii=False)[:150]}")
    else:
        print(f"  │ ❌ 結果: {result['error'][:150]}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 2: process_refund $100（許可） ──────────────────────────────

    print()
    print("  ┌─ テスト 2: process_refund $100（500未満 → 許可）────────────────")
    print(f"  │")
    print(f"  │ 🔧 ツール: process_refund")
    print(f"  │ 📥 入力:  {{\"order_id\": \"ORD-67890\", \"amount\": 100}}")
    print(f"  │ 📋 期待:  ALLOW（100 < 500 なのでポリシー条件を満たす）")
    print(f"  │")

    result = invoke_gateway_tool(config, token, "process_refund", {
        "order_id": "ORD-67890", "amount": 100, "reason": "商品破損"
    })
    if result["success"]:
        print(f"  │ ✅ 結果: ALLOW — 返金処理成功")
        print(f"  │    レスポンス: {json.dumps(result['body'], ensure_ascii=False)[:150]}")
    else:
        error = result["error"]
        if "Denied" in error or "denied" in error or "policy" in error.lower():
            print(f"  │ 🚫 結果: DENY（予期しない拒否）")
        else:
            print(f"  │ ❌ 結果: {error[:150]}")

    print(f"  └──────────────────────────────────────────────────────────────────")

    # ─── テスト 3: process_refund $1000（拒否） ─────────────────────────────

    print()
    print("  ┌─ テスト 3: process_refund $1000（500以上 → 拒否）───────────────")
    print(f"  │")
    print(f"  │ 🔧 ツール: process_refund")
    print(f"  │ 📥 入力:  {{\"order_id\": \"ORD-99999\", \"amount\": 1000}}")
    print(f"  │ 📋 期待:  DENY（1000 >= 500 なのでポリシー条件を満たさない）")
    print(f"  │")

    result = invoke_gateway_tool(config, token, "process_refund", {
        "order_id": "ORD-99999", "amount": 1000, "reason": "全額返金要求"
    })
    if result["success"]:
        print(f"  │ ⚠️  結果: ALLOW（ポリシーが効いていない可能性）")
        print(f"  │    レスポンス: {json.dumps(result['body'], ensure_ascii=False)[:150]}")
    else:
        error = result["error"]
        if "Denied" in error or "denied" in error or "policy" in error.lower() or "authorization" in error.lower():
            print(f"  │ 🚫 結果: DENY — ポリシーにより拒否!")
            print(f"  │    Cedar ポリシーが $1000 の返金をブロックしました")
        else:
            print(f"  │ ❌ 結果: {error[:150]}")

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
    print("  • Cedar ポリシーがリアルタイムでツール呼び出しを評価")
    print("  • 入力パラメータ (context.input.*) に基づく条件分岐が可能")
    print("  • ENFORCE モード: ポリシー違反は即座にブロック")
    print("  • LOG_ONLY モード: 違反をログに記録するが通過させる（テスト用）")
    print()
    print("  [ビジネスルールの例]")
    print("  • 返金上限: amount < 500")
    print("  • 部門制限: principal.department == \"finance\"")
    print("  • 時間制限: context.time.hour >= 9 && context.time.hour <= 17")
    print("  • リソース制限: resource.sensitivity != \"critical\"")
    print()


if __name__ == "__main__":
    main()
