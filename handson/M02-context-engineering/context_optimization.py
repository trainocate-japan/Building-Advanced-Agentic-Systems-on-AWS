"""
モジュール 2: 入力形式の最適化 - TOON (Token-Oriented Object Notation)

同じ情報を異なる形式で表現した場合のトークン使用量の差を比較し、
コンテキストウィンドウの効率的な利用方法を理解します。

ポイント:
- Pretty JSON は人間には読みやすいが、トークンを大量に消費する
- TOON は LLM が解析可能でありながらトークンを ~30% 削減
- 大規模運用では、この差が大きなコスト削減につながる
"""

import boto3
import json
import time

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "us.amazon.nova-pro-v1:0"


# =============================================================================
# サンプルデータ: カスタマーサポートのコンテキスト
# =============================================================================

# 形式 1: Pretty JSON（一般的な構造化データ形式）
PRETTY_JSON_CONTEXT = """{
  "context": {
    "task": "customer_support_session",
    "session_id": "sess_20260815_abc123",
    "timestamp": "2026-08-15T14:30:00Z"
  },
  "customer": {
    "id": "cust_12345",
    "name": "田中太郎",
    "plan": "Enterprise",
    "tenure_months": 24,
    "total_spend": 2400000
  },
  "agents": [
    "billing_agent",
    "technical_agent",
    "shipping_agent"
  ],
  "recent_interactions": [
    {
      "id": 1,
      "date": "2026-08-14",
      "type": "support_ticket",
      "summary": "API レート制限エラーの報告",
      "status": "resolved",
      "resolution": "プランのレート制限を一時的に引き上げ"
    },
    {
      "id": 2,
      "date": "2026-08-10",
      "type": "billing_inquiry",
      "summary": "年間契約の更新条件について",
      "status": "pending",
      "resolution": null
    },
    {
      "id": 3,
      "date": "2026-08-05",
      "type": "feature_request",
      "summary": "カスタムダッシュボード機能の追加要望",
      "status": "acknowledged",
      "resolution": "ロードマップに追加検討"
    }
  ],
  "account_settings": {
    "notification_preference": "email",
    "language": "ja",
    "timezone": "Asia/Tokyo",
    "two_factor_enabled": true,
    "api_keys_active": 3
  }
}"""

# 形式 2: TOON（Token-Oriented Object Notation）
TOON_CONTEXT = """context:
  task: customer_support_session
  session_id: sess_20260815_abc123
  timestamp: 2026-08-15T14:30:00Z
customer{id,name,plan,tenure_months,total_spend}:
  cust_12345,田中太郎,Enterprise,24,2400000
agents[3]: billing_agent,technical_agent,shipping_agent
recent_interactions[3]{id,date,type,summary,status,resolution}:
  1,2026-08-14,support_ticket,APIレート制限エラーの報告,resolved,プランのレート制限を一時的に引き上げ
  2,2026-08-10,billing_inquiry,年間契約の更新条件について,pending,null
  3,2026-08-05,feature_request,カスタムダッシュボード機能の追加要望,acknowledged,ロードマップに追加検討
account_settings{notification,lang,tz,2fa,api_keys}:
  email,ja,Asia/Tokyo,true,3"""


# =============================================================================
# トークン使用量の測定
# =============================================================================

def call_bedrock_and_measure(context: str, query: str, format_name: str) -> dict:
    """Bedrock API を呼び出してトークン使用量とレイテンシーを測定"""

    prompt = f"""以下のコンテキスト情報に基づいて質問に回答してください。

[コンテキスト]
{context}

[質問]
{query}"""

    start_time = time.time()

    response = bedrock.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 500, "temperature": 0.1}
    )

    elapsed = time.time() - start_time
    usage = response["usage"]

    return {
        "format": format_name,
        "input_tokens": usage["inputTokens"],
        "output_tokens": usage["outputTokens"],
        "total_tokens": usage["inputTokens"] + usage["outputTokens"],
        "latency_ms": round(elapsed * 1000),
        "response": response["output"]["message"]["content"][0]["text"],
        "context_chars": len(context)
    }


def run_optimization_comparison():
    """入力形式の最適化比較を実行"""

    print("=" * 70)
    print(" コンテキスト入力形式の最適化比較")
    print("=" * 70)

    # テスト質問
    queries = [
        "この顧客の直近の問い合わせ内容と対応状況を要約してください",
        "この顧客にはどのような対応優先度を設定すべきですか？理由も含めて回答してください",
    ]

    for q_idx, query in enumerate(queries, 1):
        print(f"\n{'─' * 70}")
        print(f"  質問 {q_idx}: {query}")
        print(f"{'─' * 70}")

        results = []

        # Pretty JSON で実行
        print(f"\n  [1/2] Pretty JSON 形式で実行中...")
        r1 = call_bedrock_and_measure(PRETTY_JSON_CONTEXT, query, "Pretty JSON")
        results.append(r1)
        print(f"    入力トークン: {r1['input_tokens']}")
        print(f"    レイテンシー: {r1['latency_ms']}ms")

        # TOON で実行
        print(f"  [2/2] TOON 形式で実行中...")
        r2 = call_bedrock_and_measure(TOON_CONTEXT, query, "TOON")
        results.append(r2)
        print(f"    入力トークン: {r2['input_tokens']}")
        print(f"    レイテンシー: {r2['latency_ms']}ms")

        # 比較結果
        token_reduction = r1["input_tokens"] - r2["input_tokens"]
        token_reduction_pct = (token_reduction / r1["input_tokens"]) * 100
        char_reduction = r1["context_chars"] - r2["context_chars"]
        char_reduction_pct = (char_reduction / r1["context_chars"]) * 100

        print(f"\n  ┌{'─' * 50}┐")
        print(f"  │ 比較結果                                        │")
        print(f"  ├{'─' * 50}┤")
        print(f"  │ 文字数削減: {char_reduction} 文字 ({char_reduction_pct:.1f}% 削減)     │")
        print(f"  │ トークン削減: {token_reduction} トークン ({token_reduction_pct:.1f}% 削減) │")
        print(f"  └{'─' * 50}┘")

        # 回答品質の比較
        print(f"\n  [Pretty JSON の回答]")
        print(f"  {r1['response'][:300]}...")
        print(f"\n  [TOON の回答]")
        print(f"  {r2['response'][:300]}...")

    # コスト試算
    print(f"\n{'─' * 70}")
    print("  [コスト試算] 月間 100 万リクエストの場合")
    print(f"{'─' * 70}")
    print("""
    前提: Nova Pro 入力 $0.0008/1K tokens

    Pretty JSON: ~400 tokens/request × 1,000,000 = 400M tokens
      → 月間コスト: $320

    TOON: ~280 tokens/request × 1,000,000 = 280M tokens
      → 月間コスト: $224

    削減額: $96/月 (30% 削減)
    年間: $1,152 の削減

    ※ Claude Sonnet など高単価モデルの場合、削減額はさらに大きくなる
    """)


if __name__ == "__main__":
    run_optimization_comparison()
