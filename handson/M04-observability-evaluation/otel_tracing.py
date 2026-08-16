"""
モジュール 4: OpenTelemetry 分散トレーシング - AgentCore Observability 連携

AWS Distro for OpenTelemetry (ADOT) SDK を使用して、
エージェントの実行をトレースし AgentCore Observability (CloudWatch GenAI Observability) に送信します。

セットアップ:
1. 環境変数を設定（このスクリプト内で自動設定）
2. ADOT SDK が自動でトレースを CloudWatch に送信
3. CloudWatch コンソールの GenAI Observability で確認

参考: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-get-started.html
"""

import os
import sys
import time
import uuid

# =============================================================================
# ADOT SDK のインストール確認
# =============================================================================

def ensure_adot_installed():
    """ADOT SDK がインストールされているか確認"""
    try:
        import amazon.opentelemetry.distro
        print("  ✅ ADOT SDK インストール済み")
    except ImportError:
        print("  ❌ ADOT SDK が見つかりません。以下を実行してください:")
        print("     pip install aws-opentelemetry-distro")
        sys.exit(1)


# =============================================================================
# 環境変数の設定
# =============================================================================

AGENT_NAME = "handson-demo-agent"
LOG_GROUP = f"/aws/bedrock-agentcore/runtimes/{AGENT_NAME}"

def setup_environment():
    """AgentCore Observability 用の環境変数を設定"""
    os.environ["AGENT_OBSERVABILITY_ENABLED"] = "true"
    os.environ["OTEL_PYTHON_DISTRO"] = "aws_distro"
    os.environ["OTEL_PYTHON_CONFIGURATOR"] = "aws_configurator"
    os.environ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf"
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = f"service.name={AGENT_NAME}"
    os.environ["OTEL_EXPORTER_OTLP_LOGS_HEADERS"] = (
        f"x-aws-log-group={LOG_GROUP},"
        f"x-aws-log-stream=runtime-logs,"
        f"x-aws-metric-namespace=bedrock-agentcore"
    )
    os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = (
        f"x-aws-log-group={LOG_GROUP},"
        f"x-aws-log-stream=spans"
    )

    print(f"  Agent Name: {AGENT_NAME}")
    print(f"  Log Group: {LOG_GROUP}")
    print(f"  OTLP Protocol: http/protobuf")


# =============================================================================
# トレース付きエージェント実行
# =============================================================================

def run_traced_agent():
    """Strands Agent をトレース付きで実行"""
    from strands import Agent

    # エージェント作成
    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt="""あなたはカスタマーサポートエージェントです。
顧客の問い合わせに丁寧に対応してください。必ず日本語で回答してください。""",
        name=AGENT_NAME,
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
        print(f"  Response: {str(result)[:150]}...")
        print(f"  Latency: {elapsed:.1f}s")

    return True


# =============================================================================
# メイン実行
# =============================================================================

def main():
    print("=" * 70)
    print(" OpenTelemetry トレーシング: AgentCore Observability 連携")
    print("=" * 70)

    # Step 1: ADOT SDK 確認
    print("\n[Step 1] ADOT SDK の確認...")
    ensure_adot_installed()

    # Step 2: 環境変数設定
    print("\n[Step 2] 環境変数を設定...")
    setup_environment()

    # Step 3: ロググループ作成
    print("\n[Step 3] CloudWatch ロググループを作成...")
    import boto3
    logs_client = boto3.client("logs")
    try:
        logs_client.create_log_group(logGroupName=LOG_GROUP)
        print(f"  ✅ ロググループ作成: {LOG_GROUP}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        print(f"  ✅ ロググループ既存: {LOG_GROUP}")

    # Step 4: トレース付きエージェント実行
    print("\n[Step 4] エージェントを実行（トレース送信）...")
    print("  (ADOT SDK がバックグラウンドでトレースを CloudWatch に送信します)")
    run_traced_agent()

    # Step 5: 確認手順
    print(f"\n{'─' * 70}")
    print("  [確認手順]")
    print(f"{'─' * 70}")
    print(f"""
  トレースデータが表示されるまで 2〜3 分かかります。

  確認方法:
  1. AWS コンソールで CloudWatch を開く
  2. 左メニュー「GenAI Observability」→「Bedrock AgentCore」を選択
  3. 「Agents」タブで「{AGENT_NAME}」を探す
  4. エージェントをクリックしてセッション、トレース、スパンを確認

  表示される情報:
  - Sessions: セッション数
  - Traces: 各リクエストのトレース
  - Spans: invoke_agent, chat, model invocation 等のスパン
  - Latency / Token metrics: レイテンシーとトークン使用量
    """)

    print("=" * 70)
    print(" トレーシングデモ完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
