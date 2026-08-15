"""
モジュール 3: AgentCore Policy - Cedar によるアクセス制御

Amazon Bedrock AgentCore Policy は Cedar 言語を使用して、
エージェントの行動を細粒度で制御するポリシーフレームワークです。

Cedar の特徴:
- 宣言的なポリシー言語
- permit（許可）と forbid（禁止）
- 条件付き (when/unless) でコンテキストに応じた制御
- JSON ベースのエンティティとスキーマ
"""

import boto3
import json
from datetime import datetime

# =============================================================================
# Cedar ポリシーの定義と評価
# =============================================================================

# ポリシー例 1: 金額制限付き返金ポリシー
REFUND_POLICY = """
// 500ドル未満の返金のみ許可（財務部門ユーザー限定）
permit (
    principal,
    action == MCP::Action::"process_refund",
    resource
)
when {
    principal.department == "finance" &&
    resource.amount < 500
};
"""

# ポリシー例 2: 営業時間制限
BUSINESS_HOURS_POLICY = """
// 高額操作は営業時間内のみ許可
forbid (
    principal,
    action == MCP::Action::"approve_transaction",
    resource
)
unless {
    context.current_hour >= 9 &&
    context.current_hour <= 18 &&
    context.is_business_day == true
};
"""

# ポリシー例 3: PII アクセス制限
PII_ACCESS_POLICY = """
// PII データへのアクセスは特定ロールのみ許可
permit (
    principal,
    action == MCP::Action::"access_customer_pii",
    resource
)
when {
    principal.role in ["compliance_officer", "senior_support"] &&
    principal.has_pii_training == true &&
    context.audit_logging_enabled == true
};
"""

# ポリシー例 4: エスカレーション制御
ESCALATION_POLICY = """
// エスカレーションは特定の条件でのみ許可
permit (
    principal,
    action == MCP::Action::"escalate_to_human",
    resource
)
when {
    resource.priority == "critical" ||
    resource.customer_tier == "vip" ||
    resource.failed_attempts > 3
};
"""


def demo_policy_evaluation():
    """Cedar ポリシーの評価をシミュレーション"""

    print("=" * 70)
    print(" AgentCore Policy: Cedar によるエージェント行動制御")
    print("=" * 70)

    # --- シナリオ 1: 返金処理の認可 ---
    print("\n" + "─" * 70)
    print("  シナリオ 1: 返金処理の認可判定")
    print("─" * 70)
    print(f"\n  [Cedar ポリシー]{REFUND_POLICY}")

    # テストケース
    test_cases_refund = [
        {
            "description": "財務部門、450ドルの返金",
            "principal": {"department": "finance", "username": "refund-agent"},
            "action": "process_refund",
            "resource": {"amount": 450, "order_id": "ORD-001"},
            "expected": "ALLOW"
        },
        {
            "description": "財務部門、600ドルの返金（上限超過）",
            "principal": {"department": "finance", "username": "refund-agent"},
            "action": "process_refund",
            "resource": {"amount": 600, "order_id": "ORD-002"},
            "expected": "DENY"
        },
        {
            "description": "営業部門、200ドルの返金（部門不一致）",
            "principal": {"department": "sales", "username": "sales-agent"},
            "action": "process_refund",
            "resource": {"amount": 200, "order_id": "ORD-003"},
            "expected": "DENY"
        },
    ]

    for tc in test_cases_refund:
        decision = evaluate_policy(tc["principal"], tc["action"], tc["resource"])
        status = "✅" if decision == tc["expected"] else "❌"
        print(f"  {status} {tc['description']}")
        print(f"     Principal: {tc['principal']}")
        print(f"     Resource: {tc['resource']}")
        print(f"     Decision: {decision}")
        print()

    # --- シナリオ 2: PII アクセス制御 ---
    print("─" * 70)
    print("  シナリオ 2: PII データへのアクセス制御")
    print("─" * 70)
    print(f"\n  [Cedar ポリシー]{PII_ACCESS_POLICY}")

    test_cases_pii = [
        {
            "description": "コンプライアンスオフィサー、PII研修済み",
            "principal": {"role": "compliance_officer", "has_pii_training": True},
            "action": "access_customer_pii",
            "context": {"audit_logging_enabled": True},
            "expected": "ALLOW"
        },
        {
            "description": "一般サポート、PII研修未済",
            "principal": {"role": "general_support", "has_pii_training": False},
            "action": "access_customer_pii",
            "context": {"audit_logging_enabled": True},
            "expected": "DENY"
        },
        {
            "description": "シニアサポート、監査ログ無効",
            "principal": {"role": "senior_support", "has_pii_training": True},
            "action": "access_customer_pii",
            "context": {"audit_logging_enabled": False},
            "expected": "DENY"
        },
    ]

    for tc in test_cases_pii:
        decision = evaluate_pii_policy(tc["principal"], tc["context"])
        status = "✅" if decision == tc["expected"] else "❌"
        print(f"  {status} {tc['description']}")
        print(f"     Principal: {tc['principal']}")
        print(f"     Context: {tc['context']}")
        print(f"     Decision: {decision}")
        print()

    # --- 認可フロー全体 ---
    print("─" * 70)
    print("  [認可フロー全体像]")
    print("─" * 70)
    demo_full_authorization_flow()


def evaluate_policy(principal: dict, action: str, resource: dict) -> str:
    """Cedar ポリシーの評価をシミュレート（返金ポリシー）"""
    if principal.get("department") == "finance" and resource.get("amount", 0) < 500:
        return "ALLOW"
    return "DENY"


def evaluate_pii_policy(principal: dict, context: dict) -> str:
    """Cedar ポリシーの評価をシミュレート（PII アクセスポリシー）"""
    allowed_roles = ["compliance_officer", "senior_support"]
    if (principal.get("role") in allowed_roles and
        principal.get("has_pii_training") is True and
        context.get("audit_logging_enabled") is True):
        return "ALLOW"
    return "DENY"


def demo_full_authorization_flow():
    """AgentCore Policy の完全な認可フローをデモ"""

    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │              AgentCore Policy 認可フロー                          │
    ├─────────────────────────────────────────────────────────────────┤
    │                                                                   │
    │  Step 1: JWT トークン受信                                        │
    │  ┌───────────────────────────────────────────────┐              │
    │  │ {                                              │              │
    │  │   "sub": "12345678-...",                       │              │
    │  │   "username": "refund-agent",                  │              │
    │  │   "scope": "refund:write",                     │              │
    │  │   "department": "finance"                      │              │
    │  │ }                                              │              │
    │  └───────────────────────────────────────────────┘              │
    │                         │                                        │
    │                         ▼                                        │
    │  Step 2: MCP ツールコールリクエスト                               │
    │  ┌───────────────────────────────────────────────┐              │
    │  │ {                                              │              │
    │  │   "method": "tools/call",                      │              │
    │  │   "params": {                                  │              │
    │  │     "name": "RefundTool__process_refund",      │              │
    │  │     "arguments": {"orderId": "12345",          │              │
    │  │                   "amount": 450}               │              │
    │  │   }                                            │              │
    │  │ }                                              │              │
    │  └───────────────────────────────────────────────┘              │
    │                         │                                        │
    │                         ▼                                        │
    │  Step 3: Cedar 認可リクエスト組み立て                             │
    │  principal = AgentCore::OAuthUser::"12345678-..."                │
    │  action    = AgentCore::Action::"tools/call"                    │
    │  resource  = AgentCore::Tool::"RefundTool__process_refund"      │
    │  context   = {amount: 450, department: "finance", ...}          │
    │                         │                                        │
    │                         ▼                                        │
    │  Step 4: ポリシー評価                                            │
    │  ┌────────────────────────────────────────────┐                 │
    │  │ permit when {                               │                 │
    │  │   principal.department == "finance" &&       │                 │
    │  │   resource.amount < 500                     │                 │
    │  │ }                                           │                 │
    │  │                                             │                 │
    │  │ → ALLOW ✅                                  │                 │
    │  └────────────────────────────────────────────┘                 │
    │                         │                                        │
    │                         ▼                                        │
    │  Step 5: ツール実行 or エラーレスポンス                           │
    │                                                                   │
    └─────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    demo_policy_evaluation()
    print("\n" + "=" * 70)
    print(" AgentCore Policy デモ完了")
    print("=" * 70)
    print("\n[Key Takeaways]")
    print("1. Cedar は宣言的 → ビジネスルールを自然言語に近い形で記述可能")
    print("2. permit + forbid で包括的な制御が可能")
    print("3. context でランタイム情報（時刻、ロケーション等）を活用")
    print("4. ポリシーの評価はリアルタイムで実行される")
    print("5. 監査ログと組み合わせてコンプライアンスを担保")
