"""
モジュール 1: AgentCore Memory を使用したエージェント間のメモリ共有

マルチエージェントシステムにおいて、AgentCore Memory を使用して
複数のエージェントが同じメモリリソースを共有する方法を実装します。

ポイント:
- 各エージェントは個別の actor_id を持つ（アイデンティティの維持）
- 同じ memory_id と session_id を共有（メモリの共有）
- セマンティック検索で関連メモリを取得可能
"""

import boto3
import json
import uuid
from datetime import datetime

# AgentCore Memory クライアント
bedrock_client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

# =============================================================================
# 定数定義
# =============================================================================
MEMORY_ID = "customer-support-shared-memory"
SESSION_ID = f"session-{uuid.uuid4().hex[:8]}"

# エージェント別の actor_id
CLASSIFIER_ACTOR = "classifier-agent"
TECHNICAL_ACTOR = "technical-support-agent"
BILLING_ACTOR = "billing-agent"


# =============================================================================
# メモリ操作ヘルパー関数
# =============================================================================

def write_to_shared_memory(actor_id: str, content: dict, memory_type: str = "observation"):
    """共有メモリに情報を書き込む"""
    try:
        response = bedrock_client.invoke_agent(
            # 注: 実際の AgentCore Memory API を使用
            # ここではデモ用にシミュレーション
            inputText=json.dumps({
                "action": "write_memory",
                "memory_id": MEMORY_ID,
                "actor_id": actor_id,
                "session_id": SESSION_ID,
                "content": content,
                "memory_type": memory_type,
                "timestamp": datetime.now().isoformat()
            })
        )
        return True
    except Exception as e:
        # デモ用: メモリ書き込みをシミュレート
        print(f"    [Memory Write] actor={actor_id}, type={memory_type}")
        print(f"    → {json.dumps(content, ensure_ascii=False)[:200]}")
        return True


def read_from_shared_memory(actor_id: str, search_query: str, top_k: int = 5):
    """共有メモリからセマンティック検索で情報を取得"""
    try:
        # 注: 実際の AgentCore Memory RetrieveMemoryRecords API を使用
        response = bedrock_client.retrieve_memory_records(
            memoryId=MEMORY_ID,
            namespace=f"/sessions/{SESSION_ID}",
            searchCriteria={
                "searchQuery": search_query,
                "topK": top_k
            }
        )
        return response.get("memoryRecordSummaries", [])
    except Exception as e:
        # デモ用: メモリ読み取りをシミュレート
        print(f"    [Memory Read] actor={actor_id}, query='{search_query[:50]}...'")
        return []


# =============================================================================
# マルチエージェント共有メモリのデモ
# =============================================================================

def demonstrate_shared_memory():
    """共有メモリパターンのデモンストレーション"""

    print("=" * 60)
    print(" AgentCore Memory: エージェント間メモリ共有デモ")
    print("=" * 60)
    print(f"\n  Memory ID: {MEMORY_ID}")
    print(f"  Session ID: {SESSION_ID}")
    print(f"  参加エージェント: Classifier, Technical, Billing")

    # -------------------------------------------------------------------
    # シナリオ: 顧客問い合わせのエスカレーション
    # -------------------------------------------------------------------
    print(f"\n{'─' * 60}")
    print("  シナリオ: 請求問題 → 技術的原因が判明 → エスカレーション")
    print(f"{'─' * 60}")

    customer_query = (
        "先月のAPI利用料金が通常の5倍に跳ね上がっています。"
        "何か不具合があったのではないでしょうか。"
    )
    print(f"\n  顧客問い合わせ: {customer_query}")

    # Step 1: 分類エージェントがメモリに書き込む
    print(f"\n  [Step 1] 分類エージェント → 共有メモリに書き込み")
    write_to_shared_memory(
        actor_id=CLASSIFIER_ACTOR,
        content={
            "query": customer_query,
            "category": "billing",
            "sub_category": "unexpected_charge",
            "sentiment": "frustrated",
            "priority": "high",
            "initial_routing": "billing_agent"
        },
        memory_type="classification"
    )

    # Step 2: 請求エージェントがメモリを読み、新情報を追加
    print(f"\n  [Step 2] 請求エージェント → メモリ読み取り & 書き込み")
    read_from_shared_memory(
        actor_id=BILLING_ACTOR,
        search_query="API利用料金の異常な増加"
    )
    write_to_shared_memory(
        actor_id=BILLING_ACTOR,
        content={
            "investigation": "API利用ログを確認した結果、特定の日時に異常なAPIコール急増を検出",
            "finding": "2026-07-15 03:00-05:00 に通常の100倍のリクエストが発生",
            "possible_cause": "不正アクセスまたはアプリケーションバグの可能性",
            "action_taken": "一時的な上限設定を適用",
            "escalation_needed": True,
            "escalation_to": "technical_agent"
        },
        memory_type="investigation"
    )

    # Step 3: 技術サポートエージェントが共有メモリを参照
    print(f"\n  [Step 3] 技術サポートエージェント → 共有メモリから全コンテキスト取得")
    read_from_shared_memory(
        actor_id=TECHNICAL_ACTOR,
        search_query="異常なAPIコール 不正アクセス"
    )
    write_to_shared_memory(
        actor_id=TECHNICAL_ACTOR,
        content={
            "root_cause": "顧客のAPIキーが漏洩し、第三者による不正利用と判明",
            "evidence": "リクエスト元IPが顧客の通常利用パターンと異なる",
            "resolution": [
                "APIキーを無効化し新規キー発行",
                "不正利用分の料金を返金処理",
                "IP制限の設定を推奨"
            ],
            "prevention": "APIキーローテーションの定期実施を推奨"
        },
        memory_type="resolution"
    )

    # -------------------------------------------------------------------
    # 共有メモリの活用ポイント
    # -------------------------------------------------------------------
    print(f"\n{'─' * 60}")
    print("  [共有メモリの構造]")
    print(f"{'─' * 60}")
    print("""
    ┌─────────────────────────────────────────────────────────┐
    │            AgentCore Memory (memory_id: shared)          │
    │            Session: {session_id}                         │
    ├─────────────────────────────────────────────────────────┤
    │                                                          │
    │  [classifier-agent] → classification                    │
    │    category: billing, priority: high                    │
    │                                                          │
    │  [billing-agent] → investigation                        │
    │    finding: 異常APIコール検出, escalation: technical     │
    │                                                          │
    │  [technical-agent] → resolution                         │
    │    root_cause: APIキー漏洩, resolution: キー再発行      │
    │                                                          │
    └─────────────────────────────────────────────────────────┘
    """)

    # -------------------------------------------------------------------
    # invocation_state を使用した Strands SDK の状態共有
    # -------------------------------------------------------------------
    print(f"\n{'─' * 60}")
    print("  [補足] Strands SDK invocation_state による状態共有")
    print(f"{'─' * 60}")
    print("""
    # Strands SDK では invocation_state で即時的な状態共有が可能
    
    shared_state = {
        "user_id": "customer-12345",
        "session_id": "sess-abc",
        "escalation_history": [],
        "current_priority": "high"
    }
    
    # Graph/Swarm どちらでも同じ state が自動伝搬
    result = graph(
        "請求問題を調査してください",
        invocation_state=shared_state
    )
    
    # ツール内から state にアクセス
    @tool(context=True)
    def check_billing(query: str, tool_context: ToolContext) -> str:
        user_id = tool_context.invocation_state.get("user_id")
        # パーソナライズされた処理が可能...
    """)

    print("\n" + "=" * 60)
    print(" 共有メモリデモ完了")
    print("=" * 60)
    print("\n[Key Takeaways]")
    print("1. memory_id を共有 → 同じメモリリソースにアクセス")
    print("2. actor_id で分離 → 誰が書いた情報か追跡可能")
    print("3. セマンティック検索 → 関連性の高い情報のみ取得")
    print("4. invocation_state → リアルタイムの状態共有（Strands）")
    print("5. 外部永続化 → セッションをまたいだ知識保持")


if __name__ == "__main__":
    demonstrate_shared_memory()
