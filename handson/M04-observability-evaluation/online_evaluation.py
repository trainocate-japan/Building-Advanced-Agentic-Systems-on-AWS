"""
モジュール 4 パート 3.5: AgentCore オンライン評価の設定

AgentCore Runtime エンドポイントを対象にオンライン評価を作成します。
ライブトラフィックを自動サンプリングし、組み込みエバリュエーターで
継続的に品質を評価する仕組みを構築します。

前提条件:
- AgentCore Runtime にデプロイ済みのエージェントが存在すること
  （パート 1 の ADOT トレーシングデモで作成済みのログが利用可能）
- CloudWatch Transaction Search が有効であること
"""

import boto3
import json
import time

REGION = "us-east-1"

agentcore = boto3.client("bedrock-agentcore-control", region_name=REGION)
iam = boto3.client("iam", region_name=REGION)
sts = boto3.client("sts", region_name=REGION)
logs = boto3.client("logs", region_name=REGION)


# =============================================================================
# ステップ 1: 既存の AgentCore Runtime エンドポイントを検出
# =============================================================================

def discover_agent_runtime():
    """AgentCore Runtime に登録されたエージェントを一覧表示"""

    print("\n" + "─" * 60)
    print("  ステップ 1: AgentCore Runtime エンドポイントの検出")
    print("─" * 60)

    try:
        response = agentcore.list_agent_runtimes()
        runtimes = response.get("agentRuntimes", [])

        if not runtimes:
            print("\n  ⚠️  AgentCore Runtime にデプロイされたエージェントがありません。")
            print("  → このデモでは ADOT デモで使用したロググループを直接指定します。")
            return None, None

        print(f"\n  検出されたエージェント: {len(runtimes)} 件")
        for rt in runtimes:
            print(f"    - {rt['agentRuntimeName']} (ID: {rt['agentRuntimeId']}, Status: {rt['status']})")

        # 最初の READY なランタイムを使用
        ready_runtimes = [r for r in runtimes if r.get("status") == "READY"]
        if not ready_runtimes:
            print("\n  ⚠️  READY 状態のランタイムがありません。")
            return None, None

        runtime = ready_runtimes[0]
        runtime_id = runtime["agentRuntimeId"]
        runtime_name = runtime["agentRuntimeName"]
        print(f"\n  ✅ 使用するランタイム: {runtime_name} ({runtime_id})")

        # エンドポイントを取得
        ep_response = agentcore.list_agent_runtime_endpoints(agentRuntimeId=runtime_id)
        endpoints = ep_response.get("runtimeEndpoints", [])

        if endpoints:
            endpoint = endpoints[0]
            print(f"  ✅ エンドポイント: {endpoint['name']} (Status: {endpoint['status']})")
            # runtime dict に name を統一的に設定
            runtime["_name"] = runtime_name
            return runtime, endpoint

        return runtime, None

    except Exception as e:
        print(f"\n  ℹ️  AgentCore Runtime の検出をスキップ: {e}")
        return None, None


# =============================================================================
# ステップ 2: 評価実行用 IAM ロールの作成
# =============================================================================

def create_evaluation_role():
    """オンライン評価の実行に必要な IAM ロールを作成"""

    print("\n" + "─" * 60)
    print("  ステップ 2: 評価実行用 IAM ロールの作成")
    print("─" * 60)

    account_id = sts.get_caller_identity()["Account"]
    role_name = "AgentCoreOnlineEvaluationRole"

    # 既存ロールの確認
    try:
        existing = iam.get_role(RoleName=role_name)
        role_arn = existing["Role"]["Arn"]
        print(f"\n  ✅ 既存ロールを使用: {role_arn}")
        return role_arn
    except iam.exceptions.NoSuchEntityException:
        pass

    # 信頼ポリシー
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    }
                }
            }
        ]
    }

    # ロール作成
    print(f"\n  IAM ロール作成中: {role_name}")
    response = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="IAM role for AgentCore online evaluation execution",
        Tags=[{"Key": "Project", "Value": "M04-Handson"}]
    )
    role_arn = response["Role"]["Arn"]

    # 権限ポリシーをアタッチ
    eval_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents",
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": f"arn:aws:logs:{REGION}:{account_id}:log-group:/aws/bedrock-agentcore/*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": "*"
            }
        ]
    }

    iam.put_role_policy(
        RoleName=role_name,
        PolicyName="AgentCoreOnlineEvalPolicy",
        PolicyDocument=json.dumps(eval_policy)
    )

    print(f"  ✅ ロール作成完了: {role_arn}")
    print(f"  （ロールの伝播を待機中...10 秒）")
    time.sleep(10)

    return role_arn


# =============================================================================
# ステップ 3: オンライン評価設定の作成
# =============================================================================

def create_online_evaluation(role_arn, runtime=None, endpoint=None):
    """AgentCore オンライン評価設定を作成"""

    print("\n" + "─" * 60)
    print("  ステップ 3: オンライン評価設定の作成")
    print("─" * 60)

    config_name = "m04_handson_online_eval"

    # 既存設定の確認
    try:
        existing = agentcore.list_online_evaluation_configs()
        for cfg in existing.get("onlineEvaluationConfigs", []):
            if cfg.get("onlineEvaluationConfigName") == config_name:
                print(f"\n  ✅ 既存の評価設定を検出: {config_name}")
                print(f"     ARN: {cfg['onlineEvaluationConfigArn']}")
                print(f"     Status: {cfg['status']}")
                return cfg
    except Exception:
        pass

    # データソースの設定
    if runtime and endpoint:
        # AgentCore Runtime のログ形式
        agent_id = runtime["agentRuntimeId"]
        endpoint_name = endpoint["name"]
        runtime_name = runtime.get("_name", runtime.get("agentRuntimeName", "agent"))
        log_group = f"/aws/bedrock-agentcore/runtimes/{agent_id}-{endpoint_name}"
        service_name = f"{runtime_name}.{endpoint_name}"
    else:
        # ADOT デモで使用したロググループをフォールバック
        log_group = "/aws/bedrock-agentcore/runtimes/handson-demo-agent"
        service_name = "handson-demo-agent"

    print(f"\n  データソース設定:")
    print(f"    Log Group: {log_group}")
    print(f"    Service Name: {service_name}")

    # ロググループの存在確認
    try:
        logs.describe_log_groups(logGroupNamePrefix=log_group)
        print(f"    ✅ ロググループ存在確認済み")
    except Exception:
        logs.create_log_group(logGroupName=log_group)
        print(f"    ✅ ロググループ作成済み")

    # エバリュエーターの選択
    evaluators = [
        {"evaluatorId": "Builtin.Helpfulness"},
        {"evaluatorId": "Builtin.Correctness"},
        {"evaluatorId": "Builtin.GoalSuccessRate"},
        {"evaluatorId": "Builtin.ToolSelectionAccuracy"},
    ]

    print(f"\n  エバリュエーター:")
    for ev in evaluators:
        print(f"    - {ev['evaluatorId']}")

    # オンライン評価設定の作成
    print(f"\n  オンライン評価設定を作成中: {config_name}")

    try:
        response = agentcore.create_online_evaluation_config(
            onlineEvaluationConfigName=config_name,
            description="M04 ハンズオン - AgentCore Runtime オンライン評価",
            rule={
                "samplingConfig": {
                    "samplingPercentage": 100.0  # デモ用: 全セッションを評価
                },
                "sessionConfig": {
                    "sessionTimeoutMinutes": 5  # 5分でセッション完了と判定
                }
            },
            dataSourceConfig={
                "cloudWatchLogs": {
                    "logGroupNames": [log_group],
                    "serviceNames": [service_name]
                }
            },
            evaluators=evaluators,
            evaluationExecutionRoleArn=role_arn,
            enableOnCreate=True
        )

        print(f"\n  ✅ オンライン評価設定作成完了!")
        print(f"     Config ID: {response['onlineEvaluationConfigId']}")
        print(f"     ARN: {response['onlineEvaluationConfigArn']}")
        print(f"     Status: {response['status']}")
        print(f"     Execution: {response['executionStatus']}")

        if response.get("outputConfig"):
            output_log = response["outputConfig"].get("cloudWatchConfig", {}).get("logGroupName", "N/A")
            print(f"     結果出力先: {output_log}")

        return response

    except agentcore.exceptions.ConflictException:
        print(f"\n  ℹ️  評価設定 '{config_name}' は既に存在します。")
        return None
    except Exception as e:
        print(f"\n  ❌ エラー: {e}")
        print(f"\n  [トラブルシューティング]")
        print(f"  - IAM ロールの信頼ポリシーで bedrock-agentcore.amazonaws.com を許可しているか確認")
        print(f"  - ロググループが存在するか確認: {log_group}")
        return None


# =============================================================================
# ステップ 4: 評価結果の確認方法
# =============================================================================

def show_evaluation_guidance():
    """評価結果の確認方法をガイド"""

    print("\n" + "─" * 60)
    print("  ステップ 4: 評価結果の確認")
    print("─" * 60)

    print("""
  オンライン評価は継続的に動作します。結果を確認するには:

  [方法 1: CloudWatch コンソール]
  1. CloudWatch → GenAI Observability → Bedrock AgentCore
  2. 「Evaluations」タブを選択
  3. セッション毎のエバリュエータースコアを確認

  [方法 2: CloudWatch メトリクス]
  - ネームスペース: Bedrock-AgentCore/Evaluations
  - メトリクス: 各エバリュエーターのスコア
  - ディメンション: 設定名 × エバリュエーター名

  [方法 3: CloudWatch Logs]
  - 評価結果は専用のロググループに Embedded Metric Format で出力
  - Logs Insights でクエリ可能:

    fields @timestamp, evaluator_name, score
    | filter evaluator_name = "Builtin.Helpfulness"
    | stats avg(score) as avg_score by bin(1h)

  [評価をトリガーするには]
  - パート 1 の ADOT デモ (bash run_otel_tracing.sh) を再実行
  - エージェントへのリクエストがトレースされ、オンライン評価が自動実行されます
  - 結果が表示されるまで 5-10 分かかります
    """)


# =============================================================================
# メイン実行
# =============================================================================

def run_online_evaluation_demo():
    """AgentCore オンライン評価のセットアップデモ"""

    print("=" * 70)
    print(" AgentCore オンライン評価: Runtime エンドポイントの継続的品質監視")
    print("=" * 70)
    print("""
    オンライン評価の仕組み:
    - AgentCore Runtime のライブトラフィックを自動サンプリング
    - 組み込みエバリュエーターで品質スコアを自動算出
    - 結果は CloudWatch メトリクスとして出力（アラーム連携可能）
    - セッション完了をアイドルタイムアウトで自動検出
    """)

    # ステップ 1: ランタイムの検出
    runtime, endpoint = discover_agent_runtime()

    # ステップ 2: IAM ロールの作成
    role_arn = create_evaluation_role()

    # ステップ 3: オンライン評価設定の作成
    create_online_evaluation(role_arn, runtime, endpoint)

    # ステップ 4: ガイダンス表示
    show_evaluation_guidance()

    # まとめ
    print("─" * 70)
    print("  [まとめ] オンライン評価 vs オフライン評価")
    print("─" * 70)
    print("""
    ┌──────────────────┬────────────────────┬────────────────────┐
    │                  │ オンライン評価      │ オフライン評価      │
    │                  │ (AgentCore)         │ (Bedrock Model Eval)│
    ├──────────────────┼────────────────────┼────────────────────┤
    │ データソース     │ ライブトラフィック  │ 事前準備データセット│
    │ 実行タイミング   │ 継続的・自動       │ 手動 / スケジュール │
    │ 対象             │ 本番環境           │ 開発・テスト       │
    │ サンプリング     │ 0.01% - 100%       │ 全件               │
    │ メトリクス出力   │ CloudWatch 自動    │ S3 / コンソール    │
    │ アラーム連携     │ ✅ 直接可能        │ ❌ 手動設定が必要  │
    │ ユースケース     │ 品質劣化の早期検出 │ リリース前のゲート │
    └──────────────────┴────────────────────┴────────────────────┘

    推奨: 両方を組み合わせて使用
    - リリース前: オフライン評価でゲートチェック
    - リリース後: オンライン評価で継続監視 + アラーム
    """)


if __name__ == "__main__":
    run_online_evaluation_demo()
