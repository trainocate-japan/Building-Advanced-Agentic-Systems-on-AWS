"""
モジュール 4: OpenTelemetry 分散トレーシング - AgentCore Observability 連携

ADOT (AWS Distro for OpenTelemetry) を使用して Strands Agent の実行を
AgentCore Observability (CloudWatch GenAI Observability) に送信します。

実行方法:
  bash run_otel_tracing.sh
  (環境変数のセットアップと opentelemetry-instrument 経由での実行を行います)

参考: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-get-started.html
"""

import time
from strands import Agent


# =============================================================================
# トレース付きエージェント実行
# =============================================================================

def run_traced_agent():
    """Strands Agent をトレース付きで実行"""

    print("=" * 60)
    print(" エージェント実行（ADOT トレーシング有効）")
    print("=" * 60)

    # エージェント作成
    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt="""あなたはカスタマーサポートエージェントです。
顧客の問い合わせに丁寧に対応してください。必ず日本語で回答してください。""",
    )

    # テストクエリを実行
    queries = [
        "注文 ORD-12345 の配送状況を教えてください",
        "先月の請求が高い理由を教えてください",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n  [{i}/{len(queries)}] Query: {query}")
        start = time.time()
        result = agent(query)
        elapsed = time.time() - start
        print(f"  Response: {str(result)[:200]}...")
        print(f"  Latency: {elapsed:.1f}s")

    print(f"\n{'─' * 60}")
    print("  トレースデータが AgentCore Observability に送信されました。")
    print("  CloudWatch コンソールで 2-3 分後に確認してください。")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    run_traced_agent()
