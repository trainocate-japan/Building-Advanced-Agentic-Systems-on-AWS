"""
モジュール 3: 監査ログの実装

エージェンティック AI システムの監査証跡を実装します。
すべてのエージェントアクション（ツール呼び出し、認可判定、結果）を
構造化ログとして記録します。

監査の 4 つの要素:
- 誰が (Who): エージェントを呼び出したユーザー/システム
- 何を (What): 実行されたアクション（ツール呼び出し）
- なぜ (Why): アクション選択の理由（推論過程）
- 結果 (Result): 成功/失敗/ブロック
"""

import boto3
import json
import time
import uuid
from datetime import datetime, timezone

logs_client = boto3.client("logs", region_name="us-east-1")

LOG_GROUP_NAME = "/agentic-ai/audit-logs"
LOG_STREAM_NAME = f"agent-audit-{datetime.now().strftime('%Y%m%d')}"


# =============================================================================
# 監査ログの構造定義
# =============================================================================

class AuditEvent:
    """エージェントの監査イベント"""

    def __init__(self, event_type: str, agent_id: str, user_id: str):
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type
        self.agent_id = agent_id
        self.user_id = user_id
        self.action = None
        self.resource = None
        self.parameters = {}
        self.policy_decision = None
        self.policy_id = None
        self.result = None
        self.error = None
        self.session_id = None
        self.duration_ms = None
        self.metadata = {}

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "parameters": self.parameters,
            "policy_decision": self.policy_decision,
            "policy_id": self.policy_id,
            "result": self.result,
            "error": self.error,
            "session_id": self.session_id,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


# =============================================================================
# 監査ログの書き込み
# =============================================================================

def setup_log_group():
    """CloudWatch Logs のロググループとストリームを作成"""
    try:
        logs_client.create_log_group(logGroupName=LOG_GROUP_NAME)
        print(f"  ✅ ロググループ作成: {LOG_GROUP_NAME}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"  ℹ️  ロググループ既存: {LOG_GROUP_NAME}")

    try:
        logs_client.create_log_stream(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=LOG_STREAM_NAME
        )
        print(f"  ✅ ログストリーム作成: {LOG_STREAM_NAME}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"  ℹ️  ログストリーム既存: {LOG_STREAM_NAME}")


def write_audit_log(event: AuditEvent):
    """監査イベントを CloudWatch Logs に書き込む"""
    try:
        logs_client.put_log_events(
            logGroupName=LOG_GROUP_NAME,
            logStreamName=LOG_STREAM_NAME,
            logEvents=[
                {
                    "timestamp": int(time.time() * 1000),
                    "message": json.dumps(event.to_dict(), ensure_ascii=False)
                }
            ]
        )
        return True
    except Exception as e:
        print(f"  ⚠️  ログ書き込みエラー: {e}")
        return False


# =============================================================================
# 監査ログのシミュレーション
# =============================================================================

def simulate_audit_trail():
    """エージェントの操作を監査ログとして記録するシミュレーション"""

    print("=" * 70)
    print(" エージェンティック AI 監査ログ実装")
    print("=" * 70)

    # ロググループのセットアップ
    print("\n  [ロググループセットアップ]")
    setup_log_group()

    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    user_id = "user-tanaka-12345"
    agent_id = "customer-support-agent-v2"

    print(f"\n  セッション: {session_id}")
    print(f"  ユーザー: {user_id}")
    print(f"  エージェント: {agent_id}")

    # シナリオ: 返金処理の一連のフロー
    print(f"\n{'─' * 70}")
    print("  シナリオ: 返金処理の監査証跡")
    print(f"{'─' * 70}")

    events = []

    # Event 1: セッション開始
    event1 = AuditEvent("SESSION_START", agent_id, user_id)
    event1.session_id = session_id
    event1.metadata = {"channel": "web_chat", "ip_address": "192.168.1.xxx"}
    events.append(event1)
    print(f"\n  📝 Event 1: SESSION_START")
    print(f"     {json.dumps(event1.to_dict(), ensure_ascii=False, indent=6)[:300]}")
    write_audit_log(event1)

    # Event 2: ツール呼び出し - 注文検索
    event2 = AuditEvent("TOOL_INVOCATION", agent_id, user_id)
    event2.session_id = session_id
    event2.action = "lookup_order"
    event2.resource = "orders/ORD-2026-78901"
    event2.parameters = {"order_id": "ORD-2026-78901"}
    event2.policy_decision = "ALLOW"
    event2.policy_id = "order-read-policy"
    event2.result = "SUCCESS"
    event2.duration_ms = 45
    events.append(event2)
    print(f"\n  📝 Event 2: TOOL_INVOCATION (注文検索)")
    print(f"     Action: {event2.action}")
    print(f"     Policy: {event2.policy_decision} ({event2.policy_id})")
    print(f"     Result: {event2.result} ({event2.duration_ms}ms)")
    write_audit_log(event2)

    # Event 3: ツール呼び出し - 返金処理（認可あり）
    event3 = AuditEvent("TOOL_INVOCATION", agent_id, user_id)
    event3.session_id = session_id
    event3.action = "process_refund"
    event3.resource = "refunds/ORD-2026-78901"
    event3.parameters = {"order_id": "ORD-2026-78901", "amount": 450, "reason": "defective_product"}
    event3.policy_decision = "ALLOW"
    event3.policy_id = "refund-policy-v1"
    event3.result = "SUCCESS"
    event3.duration_ms = 120
    event3.metadata = {"refund_reference": "REF-2026-001"}
    events.append(event3)
    print(f"\n  📝 Event 3: TOOL_INVOCATION (返金処理)")
    print(f"     Action: {event3.action}")
    print(f"     Parameters: amount=450, reason=defective_product")
    print(f"     Policy: {event3.policy_decision} ({event3.policy_id})")
    print(f"     Result: {event3.result}")
    write_audit_log(event3)

    # Event 4: ツール呼び出し - 高額返金（拒否）
    event4 = AuditEvent("TOOL_INVOCATION", agent_id, user_id)
    event4.session_id = session_id
    event4.action = "process_refund"
    event4.resource = "refunds/ORD-2026-78902"
    event4.parameters = {"order_id": "ORD-2026-78902", "amount": 2500, "reason": "customer_request"}
    event4.policy_decision = "DENY"
    event4.policy_id = "refund-policy-v1"
    event4.result = "BLOCKED"
    event4.error = "Amount exceeds policy limit of 500"
    event4.duration_ms = 5
    events.append(event4)
    print(f"\n  📝 Event 4: TOOL_INVOCATION (高額返金 - 拒否)")
    print(f"     Action: {event4.action}")
    print(f"     Parameters: amount=2500")
    print(f"     Policy: {event4.policy_decision} ({event4.policy_id})")
    print(f"     Result: {event4.result}")
    print(f"     Error: {event4.error}")
    write_audit_log(event4)

    # Event 5: Guardrail 介入
    event5 = AuditEvent("GUARDRAIL_INTERVENTION", agent_id, user_id)
    event5.session_id = session_id
    event5.action = "content_filter"
    event5.parameters = {"filter_type": "PII_DETECTED", "pii_type": "CREDIT_CARD"}
    event5.result = "BLOCKED"
    event5.metadata = {"guardrail_id": "grl-abc123", "action_taken": "BLOCK"}
    events.append(event5)
    print(f"\n  📝 Event 5: GUARDRAIL_INTERVENTION (PII 検出)")
    print(f"     Filter: PII_DETECTED (CREDIT_CARD)")
    print(f"     Action Taken: BLOCK")
    write_audit_log(event5)

    # Event 6: セッション終了
    event6 = AuditEvent("SESSION_END", agent_id, user_id)
    event6.session_id = session_id
    event6.duration_ms = 45000
    event6.metadata = {
        "total_tool_calls": 3,
        "blocked_calls": 1,
        "guardrail_interventions": 1,
        "resolution": "partial_refund_processed"
    }
    events.append(event6)
    print(f"\n  📝 Event 6: SESSION_END")
    print(f"     Duration: {event6.duration_ms}ms")
    print(f"     Summary: {event6.metadata}")
    write_audit_log(event6)

    # --- 監査レポート ---
    print(f"\n{'─' * 70}")
    print("  [監査レポート]")
    print(f"{'─' * 70}")
    print(f"""
    セッション: {session_id}
    ユーザー: {user_id}
    エージェント: {agent_id}

    ┌─────────────────────────────────────────────────────────────────┐
    │ イベント               │ アクション        │ 結果      │ ポリシー │
    ├─────────────────────────────────────────────────────────────────┤
    │ SESSION_START          │ -                │ -         │ -       │
    │ TOOL_INVOCATION        │ lookup_order     │ SUCCESS   │ ALLOW   │
    │ TOOL_INVOCATION        │ process_refund   │ SUCCESS   │ ALLOW   │
    │ TOOL_INVOCATION        │ process_refund   │ BLOCKED   │ DENY    │
    │ GUARDRAIL_INTERVENTION │ content_filter   │ BLOCKED   │ -       │
    │ SESSION_END            │ -                │ -         │ -       │
    └─────────────────────────────────────────────────────────────────┘

    CloudWatch Logs Insights クエリ例:
    fields @timestamp, event_type, action, policy_decision, result
    | filter session_id = "{session_id}"
    | sort @timestamp asc
    """)

    print("\n  [コンプライアンス要件への対応]")
    print("  - GDPR: PII アクセスの完全な監査証跡")
    print("  - SOX: 金融操作のポリシー判定記録")
    print("  - HIPAA: 医療情報アクセスの追跡")
    print("  - PCI-DSS: カード情報の取り扱い記録")


if __name__ == "__main__":
    simulate_audit_trail()
    print("\n" + "=" * 70)
    print(" 監査ログデモ完了")
    print("=" * 70)
