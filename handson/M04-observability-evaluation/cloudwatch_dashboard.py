"""
モジュール 4: CloudWatch ダッシュボードとアラーム

エージェント固有のカスタムメトリクスを CloudWatch に送信し、
リアルタイムモニタリングダッシュボードとアラームを構築します。
"""

import boto3
import json
import time
import random
from datetime import datetime, timezone

cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

NAMESPACE = "AgenticAI/CustomerSupport"
DASHBOARD_NAME = "AgenticAI-Observability"


# =============================================================================
# カスタムメトリクスの送信
# =============================================================================

def put_agent_metrics(agent_name: str, metrics: dict):
    """エージェントメトリクスを CloudWatch に送信"""

    metric_data = []
    dimensions = [{"Name": "AgentName", "Value": agent_name}]

    for metric_name, value in metrics.items():
        unit = "Count"
        if "latency" in metric_name.lower() or "duration" in metric_name.lower():
            unit = "Milliseconds"
        elif "token" in metric_name.lower():
            unit = "Count"
        elif "cost" in metric_name.lower():
            unit = "None"
        elif "rate" in metric_name.lower():
            unit = "Percent"

        metric_data.append({
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Dimensions": dimensions,
            "Timestamp": datetime.now(timezone.utc)
        })

    # 20 メトリクスずつバッチ送信（API 制限）
    for i in range(0, len(metric_data), 20):
        batch = metric_data[i:i+20]
        cloudwatch.put_metric_data(Namespace=NAMESPACE, MetricData=batch)


def simulate_metrics():
    """リアルなエージェントメトリクスをシミュレーション送信"""

    print("\n" + "─" * 70)
    print("  Step 1: カスタムメトリクスの送信")
    print("─" * 70)

    agents = ["orchestrator", "technical-support", "billing-support", "product-recommendation"]

    print(f"  Namespace: {NAMESPACE}")
    print(f"  エージェント: {', '.join(agents)}")
    print(f"\n  メトリクスを送信中...")

    for _ in range(5):  # 5 データポイント
        for agent in agents:
            metrics = {
                "InvocationCount": random.randint(1, 10),
                "Latency_P50": random.uniform(500, 2000),
                "Latency_P95": random.uniform(2000, 5000),
                "Latency_P99": random.uniform(5000, 10000),
                "InputTokens": random.randint(100, 500),
                "OutputTokens": random.randint(50, 300),
                "ToolCallCount": random.randint(1, 5),
                "ErrorRate": random.uniform(0, 5),
                "GuardrailInterventions": random.randint(0, 2),
                "TaskCompletionRate": random.uniform(85, 100),
            }
            put_agent_metrics(agent, metrics)

        time.sleep(1)

    print(f"  ✅ メトリクス送信完了（{len(agents)} エージェント × 5 データポイント）")


# =============================================================================
# ダッシュボード作成
# =============================================================================

def create_dashboard():
    """CloudWatch ダッシュボードを作成"""

    print("\n" + "─" * 70)
    print("  Step 2: CloudWatch ダッシュボード作成")
    print("─" * 70)

    dashboard_body = {
        "widgets": [
            # Row 1: 概要
            {
                "type": "metric",
                "x": 0, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "title": "エージェント呼び出し回数",
                    "metrics": [
                        [NAMESPACE, "InvocationCount", "AgentName", "orchestrator", {"stat": "Sum"}],
                        [NAMESPACE, "InvocationCount", "AgentName", "technical-support", {"stat": "Sum"}],
                        [NAMESPACE, "InvocationCount", "AgentName", "billing-support", {"stat": "Sum"}],
                        [NAMESPACE, "InvocationCount", "AgentName", "product-recommendation", {"stat": "Sum"}],
                    ],
                    "period": 60,
                    "view": "timeSeries",
                    "region": "us-east-1"
                }
            },
            {
                "type": "metric",
                "x": 12, "y": 0, "width": 12, "height": 6,
                "properties": {
                    "title": "レイテンシー (P50/P95/P99)",
                    "metrics": [
                        [NAMESPACE, "Latency_P50", "AgentName", "orchestrator", {"stat": "Average", "label": "P50"}],
                        [NAMESPACE, "Latency_P95", "AgentName", "orchestrator", {"stat": "Average", "label": "P95"}],
                        [NAMESPACE, "Latency_P99", "AgentName", "orchestrator", {"stat": "Average", "label": "P99"}],
                    ],
                    "period": 60,
                    "view": "timeSeries",
                    "region": "us-east-1",
                    "yAxis": {"left": {"label": "ms"}}
                }
            },
            # Row 2: トークンとコスト
            {
                "type": "metric",
                "x": 0, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "title": "トークン消費量",
                    "metrics": [
                        [NAMESPACE, "InputTokens", "AgentName", "orchestrator", {"stat": "Sum", "label": "Input"}],
                        [NAMESPACE, "OutputTokens", "AgentName", "orchestrator", {"stat": "Sum", "label": "Output"}],
                    ],
                    "period": 300,
                    "view": "timeSeries",
                    "region": "us-east-1"
                }
            },
            {
                "type": "metric",
                "x": 12, "y": 6, "width": 12, "height": 6,
                "properties": {
                    "title": "エラー率 & Guardrail 介入",
                    "metrics": [
                        [NAMESPACE, "ErrorRate", "AgentName", "orchestrator", {"stat": "Average", "label": "Error Rate %"}],
                        [NAMESPACE, "GuardrailInterventions", "AgentName", "orchestrator", {"stat": "Sum", "label": "Guardrail"}],
                    ],
                    "period": 60,
                    "view": "timeSeries",
                    "region": "us-east-1"
                }
            },
            # Row 3: 品質
            {
                "type": "metric",
                "x": 0, "y": 12, "width": 12, "height": 6,
                "properties": {
                    "title": "タスク完了率",
                    "metrics": [
                        [NAMESPACE, "TaskCompletionRate", "AgentName", "orchestrator", {"stat": "Average"}],
                        [NAMESPACE, "TaskCompletionRate", "AgentName", "technical-support", {"stat": "Average"}],
                        [NAMESPACE, "TaskCompletionRate", "AgentName", "billing-support", {"stat": "Average"}],
                    ],
                    "period": 300,
                    "view": "timeSeries",
                    "region": "us-east-1",
                    "yAxis": {"left": {"min": 0, "max": 100}}
                }
            },
            {
                "type": "metric",
                "x": 12, "y": 12, "width": 12, "height": 6,
                "properties": {
                    "title": "ツール呼び出し回数",
                    "metrics": [
                        [NAMESPACE, "ToolCallCount", "AgentName", "orchestrator", {"stat": "Sum"}],
                    ],
                    "period": 60,
                    "view": "timeSeries",
                    "region": "us-east-1"
                }
            },
        ]
    }

    cloudwatch.put_dashboard(
        DashboardName=DASHBOARD_NAME,
        DashboardBody=json.dumps(dashboard_body)
    )

    print(f"  ✅ ダッシュボード作成: {DASHBOARD_NAME}")
    print(f"  URL: https://console.aws.amazon.com/cloudwatch/home#dashboards:name={DASHBOARD_NAME}")


# =============================================================================
# アラーム設定
# =============================================================================

def create_alarms():
    """CloudWatch アラームを作成"""

    print("\n" + "─" * 70)
    print("  Step 3: アラーム設定")
    print("─" * 70)

    alarms = [
        {
            "AlarmName": "AgenticAI-HighLatency-P95",
            "MetricName": "Latency_P95",
            "Threshold": 10000,
            "ComparisonOperator": "GreaterThanThreshold",
            "EvaluationPeriods": 3,
            "Period": 60,
            "Statistic": "Average",
            "Description": "P95 レイテンシーが 10 秒を超過"
        },
        {
            "AlarmName": "AgenticAI-HighErrorRate",
            "MetricName": "ErrorRate",
            "Threshold": 5,
            "ComparisonOperator": "GreaterThanThreshold",
            "EvaluationPeriods": 2,
            "Period": 60,
            "Statistic": "Average",
            "Description": "エラー率が 5% を超過"
        },
        {
            "AlarmName": "AgenticAI-GuardrailSpike",
            "MetricName": "GuardrailInterventions",
            "Threshold": 10,
            "ComparisonOperator": "GreaterThanThreshold",
            "EvaluationPeriods": 1,
            "Period": 60,
            "Statistic": "Sum",
            "Description": "Guardrail 介入が 1 分間に 10 回を超過"
        },
    ]

    for alarm in alarms:
        cloudwatch.put_metric_alarm(
            AlarmName=alarm["AlarmName"],
            MetricName=alarm["MetricName"],
            Namespace=NAMESPACE,
            Statistic=alarm["Statistic"],
            Period=alarm["Period"],
            EvaluationPeriods=alarm["EvaluationPeriods"],
            Threshold=alarm["Threshold"],
            ComparisonOperator=alarm["ComparisonOperator"],
            AlarmDescription=alarm["Description"],
            Dimensions=[{"Name": "AgentName", "Value": "orchestrator"}],
            TreatMissingData="notBreaching"
        )
        print(f"  ✅ アラーム作成: {alarm['AlarmName']}")
        print(f"     条件: {alarm['MetricName']} > {alarm['Threshold']} ({alarm['Description']})")


# =============================================================================
# メイン実行
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print(" CloudWatch ダッシュボード & アラーム構築")
    print("=" * 70)

    simulate_metrics()
    create_dashboard()
    create_alarms()

    print("\n" + "=" * 70)
    print(" CloudWatch 構築完了")
    print("=" * 70)
    print(f"\n  ダッシュボード URL:")
    print(f"  https://console.aws.amazon.com/cloudwatch/home#dashboards:name={DASHBOARD_NAME}")
