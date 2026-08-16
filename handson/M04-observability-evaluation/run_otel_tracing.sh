#!/bin/bash
# =============================================================================
# ADOT SDK 経由でトレーシングデモを実行するラッパー
# 環境変数を設定してから opentelemetry-instrument でスクリプトを起動
# =============================================================================

AGENT_NAME="handson-demo-agent"
LOG_GROUP="/aws/bedrock-agentcore/runtimes/${AGENT_NAME}"
REGION="${AWS_REGION:-us-east-1}"

# ロググループを作成（なければ）
aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$REGION" 2>/dev/null || true

# ADOT 環境変数を設定
export AWS_REGION="$REGION"
export AWS_DEFAULT_REGION="$REGION"
export AGENT_OBSERVABILITY_ENABLED=true
export OTEL_PYTHON_DISTRO=aws_distro
export OTEL_PYTHON_CONFIGURATOR=aws_configurator
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_RESOURCE_ATTRIBUTES="service.name=${AGENT_NAME},aws.log.group.names=${LOG_GROUP}"
export OTEL_EXPORTER_OTLP_LOGS_HEADERS="x-aws-log-group=${LOG_GROUP},x-aws-log-stream=runtime-logs,x-aws-metric-namespace=bedrock-agentcore"
# スパンは aws/spans (デフォルト) に送信。カスタムロググループへの送信はリソースポリシー設定が別途必要。

echo "=============================================="
echo " ADOT トレーシングデモ"
echo "=============================================="
echo ""
echo "  Agent Name: $AGENT_NAME"
echo "  Region: $REGION"
echo "  Log Group: $LOG_GROUP"
echo ""
echo "  環境変数設定完了。opentelemetry-instrument で実行します..."
echo ""

# opentelemetry-instrument 経由で実行（自動計装）
source /home/ssm-user/.venv/bin/activate
opentelemetry-instrument python otel_tracing.py

echo ""
echo "=============================================="
echo " 完了"
echo "=============================================="
echo ""
echo " CloudWatch で確認:"
echo "   GenAI Observability → Bedrock AgentCore → Agents → ${AGENT_NAME}"
echo ""
echo " ※ トレースが表示されるまで 2-3 分かかります"
echo ""
