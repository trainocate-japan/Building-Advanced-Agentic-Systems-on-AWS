"""
モジュール 4: OpenTelemetry 分散トレーシング

OpenTelemetry SDK を使用してエージェントの実行を
トレース・スパン単位で可視化します。

トレースの階層:
- Trace: エージェント実行全体
  - Span: LLM 呼び出し
  - Span: ツール実行
  - Span: LLM 応答生成
  - ...

Strands SDK との統合:
- CallbackHandler でトレースデータを自動収集
- AgentCore Observability にエクスポート
"""

import boto3
import json
import time
import uuid
from datetime import datetime, timezone

# OpenTelemetry インポート
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("⚠️  opentelemetry がインストールされていません。シミュレーションモードで実行します。")


# =============================================================================
# OpenTelemetry セットアップ
# =============================================================================

def setup_tracer():
    """OpenTelemetry Tracer を設定"""
    if not OTEL_AVAILABLE:
        return None

    resource = Resource.create({
        "service.name": "agentic-customer-support",
        "service.version": "1.0.0",
        "deployment.environment": "demo"
    })

    provider = TracerProvider(resource=resource)

    # コンソールエクスポーター（デモ用）
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(console_exporter))

    trace.set_tracer_provider(provider)
    return trace.get_tracer("agentic-ai-tracer")


# =============================================================================
# エージェント実行のトレーシング
# =============================================================================

def simulate_traced_agent_execution(tracer):
    """エージェント実行をトレース付きでシミュレート"""

    print("=" * 70)
    print(" OpenTelemetry 分散トレーシング: エージェント実行の可視化")
    print("=" * 70)

    trace_id = uuid.uuid4().hex[:16]
    print(f"\n  Trace ID: {trace_id}")
    print(f"  サービス: agentic-customer-support")

    query = "注文 ORD-12345 の返金を処理してください。商品が破損していました。"
    print(f"  ユーザークエリ: {query}")

    print(f"\n{'─' * 70}")
    print("  [トレース構造]")
    print(f"{'─' * 70}")

    if tracer:
        # OpenTelemetry でトレース
        with tracer.start_as_current_span("agent_execution") as root_span:
            root_span.set_attribute("gen_ai.system", "aws.bedrock")
            root_span.set_attribute("agent.name", "customer-support-agent")
            root_span.set_attribute("user.query", query)
            root_span.set_attribute("session.id", f"sess-{uuid.uuid4().hex[:8]}")

            _execute_with_tracing(tracer, root_span, query)
    else:
        # シミュレーションモード
        _simulate_trace_output(query)


def _execute_with_tracing(tracer, root_span, query):
    """実際の OpenTelemetry スパンでトレース"""

    total_input_tokens = 0
    total_output_tokens = 0

    # Span 1: 意図分類 (LLM Call)
    with tracer.start_as_current_span("llm_classify_intent") as span:
        span.set_attribute("gen_ai.request.model", "us.amazon.nova-pro-v1:0")
        span.set_attribute("gen_ai.operation.name", "classify_intent")
        time.sleep(0.3)  # LLM 呼び出しシミュレート
        span.set_attribute("gen_ai.usage.input_tokens", 85)
        span.set_attribute("gen_ai.usage.output_tokens", 25)
        span.set_attribute("gen_ai.response.finish_reasons", '["end_turn"]')
        span.set_attribute("classification.result", "refund_request")
        span.set_attribute("classification.confidence", 0.95)
        total_input_tokens += 85
        total_output_tokens += 25
        print("    ├─ [Span] llm_classify_intent (300ms)")
        print("    │    model: nova-pro, tokens: 85→25, result: refund_request")

    # Span 2: ツール実行 (注文検索)
    with tracer.start_as_current_span("tool_lookup_order") as span:
        span.set_attribute("tool.name", "lookup_order")
        span.set_attribute("tool.parameters", json.dumps({"order_id": "ORD-12345"}))
        time.sleep(0.1)  # DB 検索シミュレート
        span.set_attribute("tool.result.status", "success")
        span.set_attribute("tool.result.size_bytes", 256)
        print("    ├─ [Span] tool_lookup_order (100ms)")
        print("    │    tool: lookup_order, status: success")

    # Span 3: ツール実行 (返金ポリシーチェック)
    with tracer.start_as_current_span("tool_check_refund_policy") as span:
        span.set_attribute("tool.name", "check_refund_policy")
        span.set_attribute("tool.parameters", json.dumps({"order_id": "ORD-12345", "reason": "damaged"}))
        time.sleep(0.05)
        span.set_attribute("tool.result.status", "success")
        span.set_attribute("tool.result.eligible", True)
        span.set_attribute("tool.result.max_amount", 450)
        print("    ├─ [Span] tool_check_refund_policy (50ms)")
        print("    │    tool: check_refund_policy, eligible: true")

    # Span 4: ポリシー評価 (Cedar)
    with tracer.start_as_current_span("policy_evaluation") as span:
        span.set_attribute("policy.engine", "cedar")
        span.set_attribute("policy.id", "refund-policy-v1")
        span.set_attribute("policy.decision", "ALLOW")
        time.sleep(0.01)
        print("    ├─ [Span] policy_evaluation (10ms)")
        print("    │    policy: refund-policy-v1, decision: ALLOW")

    # Span 5: ツール実行 (返金処理)
    with tracer.start_as_current_span("tool_process_refund") as span:
        span.set_attribute("tool.name", "process_refund")
        span.set_attribute("tool.parameters", json.dumps({"order_id": "ORD-12345", "amount": 450}))
        time.sleep(0.2)
        span.set_attribute("tool.result.status", "success")
        span.set_attribute("tool.result.refund_id", "REF-2026-001")
        print("    ├─ [Span] tool_process_refund (200ms)")
        print("    │    tool: process_refund, refund_id: REF-2026-001")

    # Span 6: 最終応答生成 (LLM Call)
    with tracer.start_as_current_span("llm_generate_response") as span:
        span.set_attribute("gen_ai.request.model", "us.amazon.nova-pro-v1:0")
        span.set_attribute("gen_ai.operation.name", "generate_response")
        time.sleep(0.5)
        span.set_attribute("gen_ai.usage.input_tokens", 320)
        span.set_attribute("gen_ai.usage.output_tokens", 150)
        span.set_attribute("gen_ai.response.finish_reasons", '["end_turn"]')
        total_input_tokens += 320
        total_output_tokens += 150
        print("    └─ [Span] llm_generate_response (500ms)")
        print("         model: nova-pro, tokens: 320→150")

    # ルートスパンにサマリーを設定
    root_span.set_attribute("agent.total_input_tokens", total_input_tokens)
    root_span.set_attribute("agent.total_output_tokens", total_output_tokens)
    root_span.set_attribute("agent.total_tool_calls", 3)
    root_span.set_attribute("agent.task_completion", "success")


def _simulate_trace_output(query):
    """OTEL が利用不可の場合のシミュレーション出力"""

    print("""
  Trace: agent_execution (total: 1160ms)
  │
  ├─ [Span] llm_classify_intent (300ms)
  │    Attributes:
  │      gen_ai.request.model: us.amazon.nova-pro-v1:0
  │      gen_ai.usage.input_tokens: 85
  │      gen_ai.usage.output_tokens: 25
  │      classification.result: refund_request
  │      classification.confidence: 0.95
  │
  ├─ [Span] tool_lookup_order (100ms)
  │    Attributes:
  │      tool.name: lookup_order
  │      tool.parameters: {"order_id": "ORD-12345"}
  │      tool.result.status: success
  │
  ├─ [Span] tool_check_refund_policy (50ms)
  │    Attributes:
  │      tool.name: check_refund_policy
  │      tool.result.eligible: true
  │      tool.result.max_amount: 450
  │
  ├─ [Span] policy_evaluation (10ms)
  │    Attributes:
  │      policy.engine: cedar
  │      policy.decision: ALLOW
  │
  ├─ [Span] tool_process_refund (200ms)
  │    Attributes:
  │      tool.name: process_refund
  │      tool.result.refund_id: REF-2026-001
  │
  └─ [Span] llm_generate_response (500ms)
       Attributes:
         gen_ai.request.model: us.amazon.nova-pro-v1:0
         gen_ai.usage.input_tokens: 320
         gen_ai.usage.output_tokens: 150
    """)

    # メトリクスサマリー
    print(f"{'─' * 70}")
    print("  [トレースサマリー]")
    print(f"{'─' * 70}")
    print("""
    ┌────────────────────────────────────────────────────────────────┐
    │ メトリクス            │ 値                                      │
    ├────────────────────────────────────────────────────────────────┤
    │ 全体レイテンシー       │ 1,160ms                                │
    │ LLM 呼び出し回数      │ 2                                      │
    │ LLM レイテンシー合計  │ 800ms (69%)                            │
    │ ツール呼び出し回数     │ 3                                      │
    │ ツールレイテンシー合計 │ 350ms (30%)                            │
    │ ポリシー評価           │ 10ms (1%)                              │
    │ 総入力トークン         │ 405                                    │
    │ 総出力トークン         │ 175                                    │
    │ 推定コスト             │ $0.0006                                │
    │ タスク完了             │ SUCCESS                                │
    └────────────────────────────────────────────────────────────────┘
    """)


# =============================================================================
# Strands SDK との統合方法
# =============================================================================

def show_strands_integration():
    """Strands SDK でのトレーシング統合方法を説明"""

    print(f"\n{'─' * 70}")
    print("  [参考] Strands SDK でのトレーシング統合")
    print(f"{'─' * 70}")
    print("""
    from strands import Agent
    from strands.telemetry import OTelCallbackHandler

    # OpenTelemetry ハンドラーを設定
    otel_handler = OTelCallbackHandler(
        tracer_provider=tracer_provider,
        service_name="customer-support-agent"
    )

    # エージェントにハンドラーを追加
    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt="...",
        callback_handler=otel_handler
    )

    # 通常通りエージェントを実行 → 自動的にトレースが収集される
    result = agent("注文の返金を処理してください")

    # AgentCore Observability にエクスポート
    # → AgentCore コンソールでトレースを可視化
    # → CloudWatch にメトリクスを送信
    """)


# =============================================================================
# メイン実行
# =============================================================================

if __name__ == "__main__":
    tracer = setup_tracer()
    simulate_traced_agent_execution(tracer)
    show_strands_integration()

    print("\n" + "=" * 70)
    print(" OpenTelemetry トレーシングデモ完了")
    print("=" * 70)
    print("\n[Key Takeaways]")
    print("1. トレース = エージェント実行全体、スパン = 個々のステップ")
    print("2. LLM 呼び出しがレイテンシーの大部分を占める（69%）")
    print("3. ツール実行時間はボトルネック特定に有用")
    print("4. トークン数のトレースでコスト管理が可能")
    print("5. Strands SDK のフック機構で自動トレース収集")
