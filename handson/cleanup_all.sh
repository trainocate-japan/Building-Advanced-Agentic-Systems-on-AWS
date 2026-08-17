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

# AgentCore Gateway Target + Gateway の削除
echo "  AgentCore Gateway の削除..."
GATEWAY_ID=$(aws bedrock-agentcore-control list-gateways --region "$REGION" \
    --query "gateways[?name=='agentcore-handson-gateway'].gatewayId" \
    --output text 2>/dev/null || echo "")
if [ -n "$GATEWAY_ID" ] && [ "$GATEWAY_ID" != "None" ]; then
    # Target 削除
    TARGET_IDS=$(aws bedrock-agentcore-control list-gateway-targets \
        --gateway-identifier "$GATEWAY_ID" --region "$REGION" \
        --query "targets[].targetId" --output text 2>/dev/null || echo "")
    for tid in $TARGET_IDS; do
        aws bedrock-agentcore-control delete-gateway-target \
            --gateway-identifier "$GATEWAY_ID" --target-id "$tid" --region "$REGION" 2>/dev/null && \
            echo "  ✅ Gateway Target 削除: $tid" || true
    done
    sleep 5
    # Gateway 削除
    aws bedrock-agentcore-control delete-gateway \
        --gateway-identifier "$GATEWAY_ID" --region "$REGION" 2>/dev/null && \
        echo "  ✅ Gateway 削除: $GATEWAY_ID" || \
        echo "  ⚠️  Gateway 削除失敗"
else
    echo "  ─ Gateway なし（スキップ）"
fi

# Policy Engine の削除
echo "  Policy Engine の削除..."
PE_ID=$(aws bedrock-agentcore-control list-policy-engines --region "$REGION" \
    --query "policyEngines[?name=='agentcore-handson-policy-engine'].policyEngineId" \
    --output text 2>/dev/null || echo "")
if [ -n "$PE_ID" ] && [ "$PE_ID" != "None" ]; then
    # Policy 削除
    POLICY_IDS=$(aws bedrock-agentcore-control list-policies \
        --policy-engine-id "$PE_ID" --region "$REGION" \
        --query "policies[].policyId" --output text 2>/dev/null || echo "")
    for pid in $POLICY_IDS; do
        aws bedrock-agentcore-control delete-policy \
            --policy-engine-id "$PE_ID" --policy-id "$pid" --region "$REGION" 2>/dev/null && \
            echo "  ✅ Policy 削除: $pid" || true
    done
    sleep 3
    aws bedrock-agentcore-control delete-policy-engine \
        --policy-engine-id "$PE_ID" --region "$REGION" 2>/dev/null && \
        echo "  ✅ Policy Engine 削除: $PE_ID" || \
        echo "  ⚠️  Policy Engine 削除失敗"
else
    echo "  ─ Policy Engine なし（スキップ）"
fi

# Lambda 関数の削除
echo "  Lambda 関数の削除..."
aws lambda delete-function --function-name agentcore-handson-tools --region "$REGION" 2>/dev/null && \
    echo "  ✅ Lambda 削除: agentcore-handson-tools" || \
    echo "  ─ Lambda なし（スキップ）"

# IAM ロールの削除 (Gateway + Lambda)
echo "  IAM ロールの削除..."
for ROLE in AgentCoreHandsonGatewayRole AgentCoreHandsonLambdaRole; do
    # インラインポリシー削除
    POLICIES=$(aws iam list-role-policies --role-name "$ROLE" --query "PolicyNames[]" --output text 2>/dev/null || echo "")
    for p in $POLICIES; do
        aws iam delete-role-policy --role-name "$ROLE" --policy-name "$p" 2>/dev/null
    done
    # マネージドポリシーデタッチ
    ATTACHED=$(aws iam list-attached-role-policies --role-name "$ROLE" --query "AttachedPolicies[].PolicyArn" --output text 2>/dev/null || echo "")
    for arn in $ATTACHED; do
        aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$arn" 2>/dev/null
    done
    aws iam delete-role --role-name "$ROLE" 2>/dev/null && \
        echo "  ✅ IAM ロール削除: $ROLE" || \
        echo "  ─ IAM ロールなし: $ROLE（スキップ）"
done

# Cognito User Pool の削除
echo "  Cognito User Pool の削除..."
POOL_ID=$(aws cognito-idp list-user-pools --max-results 20 --region "$REGION" \
    --query "UserPools[?Name=='AgentCoreIdentityHandsonPool'].Id" \
    --output text 2>/dev/null || echo "")

if [ -n "$POOL_ID" ] && [ "$POOL_ID" != "None" ]; then
    DOMAIN=$(aws cognito-idp describe-user-pool --user-pool-id "$POOL_ID" --region "$REGION" \
        --query "UserPool.Domain" --output text 2>/dev/null || echo "")
    if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "None" ]; then
        aws cognito-idp delete-user-pool-domain \
            --domain "$DOMAIN" --user-pool-id "$POOL_ID" --region "$REGION" 2>/dev/null && \
            echo "  ✅ Cognito ドメイン削除: $DOMAIN" || true
    fi
    aws cognito-idp delete-user-pool --user-pool-id "$POOL_ID" --region "$REGION" 2>/dev/null && \
        echo "  ✅ User Pool 削除: $POOL_ID" || \
        echo "  ⚠️  User Pool 削除失敗"
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
