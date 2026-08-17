#!/bin/bash
# =============================================================================
# Building Advanced Agentic Systems on AWS - 全リソースクリーンアップ
# =============================================================================
# 全モジュールで作成した AWS リソースを一括削除するスクリプト
# 冪等: リソースが存在しなければスキップ
# =============================================================================

set -e

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")

echo "=============================================="
echo " リソースクリーンアップ"
echo "=============================================="
echo ""
echo "  アカウント: $ACCOUNT_ID"
echo "  リージョン: $REGION"
echo ""
echo "  対象モジュール: M01〜M04"
echo ""
read -p "  続行しますか？ (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "  キャンセルしました。"
    exit 0
fi

echo ""

# =============================================================================
# M03: セキュリティ関連リソース
# =============================================================================
echo "──────────────────────────────────────────────"
echo " [M03] セキュリティ関連リソースの削除"
echo "──────────────────────────────────────────────"

# AgentCore Credential Provider の削除
echo "  AgentCore Credential Provider の削除..."
PROVIDER_NAME="AgentCoreHandsonProvider"
aws bedrock-agentcore-control delete-oauth2-credential-provider \
    --name "$PROVIDER_NAME" --region "$REGION" 2>/dev/null && \
    echo "  ✅ Credential Provider 削除: $PROVIDER_NAME" || \
    echo "  ─ Credential Provider なし（スキップ）"

# Cognito User Pool の削除 (AgentCore Identity デモ用)
echo "  Cognito User Pool の削除..."
POOL_ID=$(aws cognito-idp list-user-pools --max-results 20 --region "$REGION" \
    --query "UserPools[?Name=='AgentCoreIdentityHandsonPool'].Id" \
    --output text 2>/dev/null || echo "")

if [ -n "$POOL_ID" ] && [ "$POOL_ID" != "None" ]; then
    # ドメイン削除（User Pool 削除前に必要）
    DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id "$POOL_ID" --region "$REGION" \
        --query "UserPool.Domain" --output text 2>/dev/null || echo "")
    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "None" ]; then
        aws cognito-idp delete-user-pool-domain \
            --domain "$DOMAIN" --user-pool-id "$POOL_ID" --region "$REGION" 2>/dev/null && \
            echo "  ✅ Cognito ドメイン削除: $DOMAIN" || \
            echo "  ⚠️  ドメイン削除失敗"
    fi
    # User Pool 削除
    aws cognito-idp delete-user-pool --user-pool-id "$POOL_ID" --region "$REGION" 2>/dev/null && \
        echo "  ✅ User Pool 削除: $POOL_ID" || \
        echo "  ⚠️  User Pool 削除失敗（手動で確認してください）"
else
    echo "  ─ Cognito User Pool なし（スキップ）"
fi

# Identity 設定ファイルの削除
IDENTITY_CONFIG="$HOME/handson/M03-security-compliance/identity_config.json"
if [ -f "$IDENTITY_CONFIG" ]; then
    rm -f "$IDENTITY_CONFIG"
    echo "  ✅ 設定ファイル削除: identity_config.json"
else
    echo "  ─ identity_config.json なし（スキップ）"
fi

# Bedrock Guardrail の削除
echo "  Guardrail の削除..."
GUARDRAIL_ID=$(aws bedrock list-guardrails --region "$REGION" \
    --query "guardrails[?name=='agentic-security-guardrail'].id" \
    --output text 2>/dev/null || echo "")

if [ -n "$GUARDRAIL_ID" ] && [ "$GUARDRAIL_ID" != "None" ]; then
    aws bedrock delete-guardrail --guardrail-identifier "$GUARDRAIL_ID" --region "$REGION" 2>/dev/null && \
        echo "  ✅ Guardrail 削除: $GUARDRAIL_ID" || \
        echo "  ⚠️  Guardrail 削除失敗（手動で確認してください）"
else
    echo "  ─ Guardrail なし（スキップ）"
fi

# CloudWatch ロググループ (監査ログ)
echo "  監査ログの削除..."
aws logs delete-log-group --log-group-name "/agentic-ai/audit-logs" --region "$REGION" 2>/dev/null && \
    echo "  ✅ ロググループ削除: /agentic-ai/audit-logs" || \
    echo "  ─ ロググループなし（スキップ）"

echo ""

# =============================================================================
# M04: モニタリング関連リソース
# =============================================================================
echo "──────────────────────────────────────────────"
echo " [M04] モニタリング関連リソースの削除"
echo "──────────────────────────────────────────────"

# CloudWatch ダッシュボード
echo "  CloudWatch ダッシュボードの削除..."
aws cloudwatch delete-dashboards --dashboard-names "AgenticAI-Observability" --region "$REGION" 2>/dev/null && \
    echo "  ✅ ダッシュボード削除: AgenticAI-Observability" || \
    echo "  ─ ダッシュボードなし（スキップ）"

# CloudWatch アラーム
echo "  CloudWatch アラームの削除..."
ALARMS=$(aws cloudwatch describe-alarms --alarm-name-prefix "AgenticAI-" --region "$REGION" \
    --query "MetricAlarms[].AlarmName" --output text 2>/dev/null || echo "")

if [ -n "$ALARMS" ] && [ "$ALARMS" != "None" ]; then
    for alarm in $ALARMS; do
        aws cloudwatch delete-alarms --alarm-names "$alarm" --region "$REGION" 2>/dev/null && \
            echo "  ✅ アラーム削除: $alarm" || \
            echo "  ⚠️  アラーム削除失敗: $alarm"
    done
else
    echo "  ─ アラームなし（スキップ）"
fi

echo ""

# =============================================================================
# M01: マルチエージェント関連リソース
# =============================================================================
echo "──────────────────────────────────────────────"
echo " [M01] マルチエージェント関連リソースの削除"
echo "──────────────────────────────────────────────"

# CloudFormation スタック (M01)
echo "  CloudFormation スタックの削除..."
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name "m01-multi-agent" --region "$REGION" \
    --query "Stacks[0].StackStatus" --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$STACK_STATUS" != "NOT_FOUND" ]; then
    aws cloudformation delete-stack --stack-name "m01-multi-agent" --region "$REGION"
    echo "  ⏳ スタック削除中: m01-multi-agent"
    aws cloudformation wait stack-delete-complete --stack-name "m01-multi-agent" --region "$REGION" 2>/dev/null && \
        echo "  ✅ スタック削除完了: m01-multi-agent" || \
        echo "  ⚠️  スタック削除タイムアウト（手動で確認してください）"
else
    echo "  ─ スタックなし（スキップ）"
fi

echo ""

# =============================================================================
# 共通リソース
# =============================================================================
echo "──────────────────────────────────────────────"
echo " [共通] その他のリソースの削除"
echo "──────────────────────────────────────────────"

# AgentCore 関連のロググループ
echo "  AgentCore ロググループの削除..."
for log_group in "/aws/bedrock/agentcore" "/agentic-ai"; do
    aws logs delete-log-group --log-group-name "$log_group" --region "$REGION" 2>/dev/null && \
        echo "  ✅ ロググループ削除: $log_group" || \
        echo "  ─ ロググループなし: $log_group（スキップ）"
done

# カスタムメトリクス（削除不可のため通知のみ）
echo ""
echo "  ℹ️  CloudWatch カスタムメトリクス (AgenticAI/CustomerSupport) は"
echo "     自動的に期限切れになります（15ヶ月後）。手動削除は不要です。"

echo ""

# =============================================================================
# 完了
# =============================================================================
echo "=============================================="
echo " クリーンアップ完了!"
echo "=============================================="
echo ""
echo "  削除されたリソース:"
echo "  - AgentCore Credential Provider (AgentCoreHandsonProvider)"
echo "  - Cognito User Pool (AgentCoreIdentityHandsonPool)"
echo "  - Bedrock Guardrail (agentic-security-guardrail)"
echo "  - CloudWatch ダッシュボード (AgenticAI-Observability)"
echo "  - CloudWatch アラーム (AgenticAI-* )"
echo "  - CloudWatch ロググループ (監査ログ)"
echo "  - CloudFormation スタック (m01-multi-agent)"
echo ""
echo "  ⚠️  以下は手動確認が必要な場合があります:"
echo "  - AgentCore Memory セッション"
echo "  - Bedrock 評価ジョブ"
echo "  - AgentCore Policy ストア"
echo ""
