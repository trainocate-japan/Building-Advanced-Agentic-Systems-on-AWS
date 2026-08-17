"""
モジュール 3: AgentCore Identity + Policy - フルセットアップ

以下のリソースを作成し、Identity (認証) と Policy (認可) のデモ基盤を構築します:

[Identity 基盤]
1. Cognito User Pool + ドメイン + Resource Server
2. App Client (2LO用 / 3LO用)
3. テストユーザー
4. AgentCore Credential Provider

[Gateway + Policy 基盤]
5. モック Lambda 関数 (process_refund / get_order_status)
6. Gateway 用 IAM ロール
7. AgentCore Gateway (JWT Authorizer 付き)
8. Gateway Target (Lambda)
9. Policy Engine + Cedar Policy

設定情報は identity_config.json に保存され、後続のデモで使用されます。
"""

import boto3
import json
import time
import random
import string
import zipfile
import io

# =============================================================================
# 設定
# =============================================================================

REGION = "us-east-1"
POOL_NAME = "AgentCoreIdentityHandsonPool"
CLIENT_NAME = "AgentCoreHandsonClient"
CREDENTIAL_PROVIDER_NAME = "AgentCoreHandsonProvider"
RESOURCE_SERVER_ID = "agentcore-demo-api"
RESOURCE_SERVER_NAME = "AgentCore Demo API"
GATEWAY_NAME = "agentcore-handson-gateway"
GATEWAY_ROLE_NAME = "AgentCoreHandsonGatewayRole"
LAMBDA_ROLE_NAME = "AgentCoreHandsonLambdaRole"
LAMBDA_FUNCTION_NAME = "agentcore-handson-tools"
POLICY_ENGINE_NAME = "agentcore_handson_policy_engine"
CONFIG_FILE = "identity_config.json"


# =============================================================================
# ヘルパー関数
# =============================================================================

def print_header(title):
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print(f"║  {title:<66} ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()


def print_step(step_num, title):
    print()
    print(f"  ┌─ Step {step_num} ──────────────────────────────────────────────────────")
    print(f"  │ {title}")
    print(f"  │")


def print_info(key, value):
    print(f"  │ 📋 {key}: {value}")


def print_success(message):
    print(f"  │ ✅ {message}")


def print_wait(message):
    print(f"  │ ⏳ {message}")


def print_end():
    print(f"  └──────────────────────────────────────────────────────────────────")


def random_suffix(length=5):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_account_id():
    sts = boto3.client("sts", region_name=REGION)
    return sts.get_caller_identity()["Account"]


def wait_for_status(client, get_func, expected_statuses, description, max_wait=180):
    """リソースのステータスが期待値のいずれかになるまで待機"""
    if isinstance(expected_statuses, str):
        expected_statuses = [expected_statuses]
    print_wait(f"{description} の準備完了を待機中...")
    for i in range(max_wait // 5):
        try:
            response = get_func()
            status = response.get("status", "UNKNOWN")
            if status in expected_statuses:
                print_success(f"{description}: {status}")
                return response
            if status in ("FAILED", "DELETE_FAILED"):
                raise Exception(f"{description} が失敗しました: {status}")
        except Exception as e:
            if "not found" in str(e).lower() or "NotFound" in str(e):
                pass
            else:
                raise
        time.sleep(5)
    raise Exception(f"{description} がタイムアウトしました（最終ステータス: {status}）")


# =============================================================================
# メイン
# =============================================================================

def main():
    print_header("AgentCore Identity + Policy フルセットアップ")

    print("  以下のリソースを作成します:")
    print("    [Identity]")
    print("    1. Cognito User Pool + ドメイン + Resource Server")
    print("    2. App Client (2LO/3LO)")
    print("    3. テストユーザー")
    print("    4. AgentCore Credential Provider")
    print("    [Gateway + Policy]")
    print("    5. モック Lambda (process_refund / get_order_status)")
    print("    6. Gateway 用 IAM ロール")
    print("    7. AgentCore Gateway")
    print("    8. Gateway Target (Lambda)")
    print("    9. Policy Engine + Cedar Policy")
    print()

    account_id = get_account_id()
    print(f"  Account ID: {account_id}")
    print(f"  Region: {REGION}")
    print()

    cognito_client = boto3.client("cognito-idp", region_name=REGION)
    agentcore_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    iam_client = boto3.client("iam", region_name=REGION)
    lambda_client = boto3.client("lambda", region_name=REGION)

    # =========================================================================
    # Step 1: Cognito User Pool
    # =========================================================================
    print_step(1, "Cognito User Pool + ドメイン + Resource Server")

    response = cognito_client.create_user_pool(
        PoolName=POOL_NAME,
        Policies={"PasswordPolicy": {
            "MinimumLength": 8, "RequireUppercase": True,
            "RequireLowercase": True, "RequireNumbers": True,
            "RequireSymbols": False,
        }},
        AutoVerifiedAttributes=["email"],
        Schema=[{"Name": "email", "AttributeDataType": "String",
                 "Required": True, "Mutable": True}],
    )
    user_pool_id = response["UserPool"]["Id"]
    print_success(f"User Pool: {user_pool_id}")

    domain_name = f"agentcore-handson-{random_suffix()}"
    cognito_client.create_user_pool_domain(Domain=domain_name, UserPoolId=user_pool_id)
    print_success(f"ドメイン: {domain_name}")

    cognito_client.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=RESOURCE_SERVER_ID,
        Name=RESOURCE_SERVER_NAME,
        Scopes=[
            {"ScopeName": "read", "ScopeDescription": "読み取り"},
            {"ScopeName": "write", "ScopeDescription": "書き込み"},
        ],
    )
    print_success(f"Resource Server: {RESOURCE_SERVER_ID}")
    print_end()

    # =========================================================================
    # Step 2: App Clients
    # =========================================================================
    print_step(2, "App Client 作成（2LO用 + 3LO用）")

    # 2LO
    resp_2lo = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f"{CLIENT_NAME}-2LO",
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=[f"{RESOURCE_SERVER_ID}/read", f"{RESOURCE_SERVER_ID}/write"],
        AllowedOAuthFlowsUserPoolClient=True,
    )
    client_id_2lo = resp_2lo["UserPoolClient"]["ClientId"]
    client_secret_2lo = resp_2lo["UserPoolClient"]["ClientSecret"]
    print_success(f"2LO Client: {client_id_2lo}")

    # 3LO
    resp_3lo = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f"{CLIENT_NAME}-3LO",
        GenerateSecret=True,
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "profile", "email"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        CallbackURLs=["https://localhost/callback"],
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
        ],
    )
    client_id_3lo = resp_3lo["UserPoolClient"]["ClientId"]
    client_secret_3lo = resp_3lo["UserPoolClient"]["ClientSecret"]
    print_success(f"3LO Client: {client_id_3lo}")
    print_end()

    # =========================================================================
    # Step 3: テストユーザー
    # =========================================================================
    print_step(3, "テストユーザー作成")

    username = f"testuser-{random_suffix()}"
    password = f"TestPass{random_suffix(6)}!1"
    cognito_client.admin_create_user(
        UserPoolId=user_pool_id, Username=username,
        TemporaryPassword=password, MessageAction="SUPPRESS",
        UserAttributes=[
            {"Name": "email", "Value": f"{username}@example.com"},
            {"Name": "email_verified", "Value": "true"},
        ],
    )
    cognito_client.admin_set_user_password(
        UserPoolId=user_pool_id, Username=username,
        Password=password, Permanent=True,
    )
    print_success(f"ユーザー: {username}")
    print_end()

    # =========================================================================
    # Step 4: AgentCore Credential Provider
    # =========================================================================
    print_step(4, "AgentCore Credential Provider")

    issuer_url = (
        f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}"
        f"/.well-known/openid-configuration"
    )

    try:
        resp = agentcore_client.create_oauth2_credential_provider(
            name=CREDENTIAL_PROVIDER_NAME,
            credentialProviderVendor="CustomOauth2",
            oauth2ProviderConfigInput={
                "customOauth2ProviderConfig": {
                    "oauthDiscovery": {"discoveryUrl": issuer_url},
                    "clientId": client_id_3lo,
                    "clientSecret": client_secret_3lo,
                }
            },
        )
        callback_url = resp.get("callbackUrl", "N/A")
        provider_arn = resp.get("credentialProviderArn", "N/A")
        print_success(f"Credential Provider 作成: {CREDENTIAL_PROVIDER_NAME}")
    except Exception as e:
        if "already exists" in str(e) or "ValidationException" in str(type(e).__name__):
            resp = agentcore_client.get_oauth2_credential_provider(name=CREDENTIAL_PROVIDER_NAME)
            callback_url = resp.get("callbackUrl", "N/A")
            provider_arn = resp.get("credentialProviderArn", "N/A")
            print_success(f"Credential Provider 既存（スキップ）: {CREDENTIAL_PROVIDER_NAME}")
        else:
            raise
    print_info("Callback URL", callback_url)

    # 3LO クライアントに Callback URL 登録
    cognito_client.update_user_pool_client(
        UserPoolId=user_pool_id, ClientId=client_id_3lo,
        ClientName=f"{CLIENT_NAME}-3LO",
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "profile", "email"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        CallbackURLs=[callback_url],
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
        ],
    )
    print_success("Callback URL を 3LO Client に登録")
    print_end()

    # =========================================================================
    # Step 5: モック Lambda 関数
    # =========================================================================
    print_step(5, "モック Lambda 関数 (process_refund / get_order_status)")

    # Lambda 実行ロール作成
    try:
        iam_client.create_role(
            RoleName=LAMBDA_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }]
            }),
        )
        iam_client.attach_role_policy(
            RoleName=LAMBDA_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        print_success(f"Lambda ロール作成: {LAMBDA_ROLE_NAME}")
        time.sleep(10)  # ロール伝搬待ち
    except iam_client.exceptions.EntityAlreadyExistsException:
        print_success(f"Lambda ロール既存: {LAMBDA_ROLE_NAME}")

    lambda_role_arn = f"arn:aws:iam::{account_id}:role/{LAMBDA_ROLE_NAME}"

    # Lambda コード作成
    lambda_code = '''
import json

def handler(event, context):
    """AgentCore Gateway から呼び出されるモックツール"""
    # Gateway からのリクエストを解析
    body = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))
    tool_name = body.get("tool_name", body.get("name", "unknown"))
    tool_input = body.get("tool_input", body.get("input", {}))

    if tool_name == "process_refund":
        amount = tool_input.get("amount", 0)
        order_id = tool_input.get("order_id", "unknown")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "result": "success",
                "message": f"Refund of ${amount} processed for order {order_id}",
                "refund_id": f"REF-{context.aws_request_id[:8]}",
            })
        }
    elif tool_name == "get_order_status":
        order_id = tool_input.get("order_id", "unknown")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "result": "success",
                "order_id": order_id,
                "status": "shipped",
                "tracking_number": "1Z999AA10123456784",
            })
        }
    else:
        return {
            "statusCode": 200,
            "body": json.dumps({
                "result": "success",
                "message": f"Tool '{tool_name}' executed successfully",
                "input": tool_input,
            })
        }
'''

    # zip パッケージ作成
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lambda_function.py", lambda_code)
    zip_buffer.seek(0)

    # Lambda 作成 or 更新
    try:
        lambda_client.create_function(
            FunctionName=LAMBDA_FUNCTION_NAME,
            Runtime="python3.12",
            Role=lambda_role_arn,
            Handler="lambda_function.handler",
            Code={"ZipFile": zip_buffer.read()},
            Timeout=30,
            Description="AgentCore Gateway ハンズオン用モックツール",
        )
        print_success(f"Lambda 作成: {LAMBDA_FUNCTION_NAME}")
    except lambda_client.exceptions.ResourceConflictException:
        zip_buffer.seek(0)
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_buffer.read(),
        )
        print_success(f"Lambda 更新: {LAMBDA_FUNCTION_NAME}")

    lambda_arn = f"arn:aws:lambda:{REGION}:{account_id}:function:{LAMBDA_FUNCTION_NAME}"

    # Lambda の resource-based policy で Gateway からの呼び出しを許可
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId="AllowBedrockAgentCore",
            Action="lambda:InvokeFunction",
            Principal="bedrock-agentcore.amazonaws.com",
            SourceAccount=account_id,
        )
        print_success("Lambda にInvoke許可を追加")
    except lambda_client.exceptions.ResourceConflictException:
        print_success("Lambda のInvoke許可は既存")

    print_end()

    # =========================================================================
    # Step 6: Gateway 用 IAM ロール
    # =========================================================================
    print_step(6, "Gateway 用 IAM ロール")

    gateway_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole",
            "Condition": {
                "StringEquals": {"aws:SourceAccount": account_id},
                "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:*"},
            },
        }]
    }

    try:
        iam_client.create_role(
            RoleName=GATEWAY_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(gateway_trust_policy),
        )
        print_success(f"Gateway ロール作成: {GATEWAY_ROLE_NAME}")
    except iam_client.exceptions.EntityAlreadyExistsException:
        # 既存の場合は trust policy を更新
        iam_client.update_assume_role_policy(
            RoleName=GATEWAY_ROLE_NAME,
            PolicyDocument=json.dumps(gateway_trust_policy),
        )
        print_success(f"Gateway ロール既存（trust policy 更新）: {GATEWAY_ROLE_NAME}")

    gateway_permission_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "InvokeLambda",
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_arn,
            },
            {
                "Sid": "PolicyEngine",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetPolicyEngine",
                    "bedrock-agentcore:AuthorizeAction",
                    "bedrock-agentcore:PartiallyAuthorizeActions",
                ],
                "Resource": f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:*",
            },
            {
                "Sid": "Logs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                "Resource": "*",
            },
        ]
    }

    iam_client.put_role_policy(
        RoleName=GATEWAY_ROLE_NAME,
        PolicyName="GatewayPermissions",
        PolicyDocument=json.dumps(gateway_permission_policy),
    )
    print_success("Gateway ロールに権限を付与")

    gateway_role_arn = f"arn:aws:iam::{account_id}:role/{GATEWAY_ROLE_NAME}"
    time.sleep(10)  # ロール伝搬待ち
    print_end()

    # =========================================================================
    # Step 7: Policy Engine
    # =========================================================================
    print_step(7, "Policy Engine 作成")

    policy_engine_id = None
    policy_engine_arn = None

    try:
        resp = agentcore_client.create_policy_engine(
            name=POLICY_ENGINE_NAME,
            description="AgentCore ハンズオン用 Policy Engine",
        )
        policy_engine_id = resp["policyEngineId"]
        policy_engine_arn = resp["policyEngineArn"]
        print_success(f"Policy Engine 作成: {policy_engine_id}")
    except Exception as e:
        if "already exists" in str(e) or "Conflict" in str(e):
            engines = agentcore_client.list_policy_engines()
            items = engines.get("items", engines.get("policyEngines", []))
            for eng in items:
                if eng.get("name") == POLICY_ENGINE_NAME:
                    policy_engine_id = eng["policyEngineId"]
                    policy_engine_arn = eng.get("policyEngineArn",
                        f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:policy-engine/{eng['policyEngineId']}")
                    break
            if policy_engine_id:
                print_success(f"Policy Engine 既存（スキップ）: {policy_engine_id}")
            else:
                raise Exception("Policy Engine が既存だが一覧から見つからない")
        else:
            raise

    print_info("Policy Engine ID", policy_engine_id)
    print_info("Policy Engine ARN", policy_engine_arn)

    # ACTIVE になるまで待機
    wait_for_status(
        agentcore_client,
        lambda: agentcore_client.get_policy_engine(policyEngineId=policy_engine_id),
        "ACTIVE",
        "Policy Engine",
    )
    print_end()

    # =========================================================================
    # Step 8: AgentCore Gateway
    # =========================================================================
    print_step(8, "AgentCore Gateway 作成 (JWT Authorizer + Policy Engine)")

    discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"

    try:
        resp = agentcore_client.create_gateway(
            name=GATEWAY_NAME,
            protocolType="MCP",
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": discovery_url,
                    "allowedClients": [client_id_2lo, client_id_3lo],
                }
            },
            roleArn=gateway_role_arn,
            policyEngineConfiguration={
                "mode": "ENFORCE",
                "arn": policy_engine_arn,
            },
        )
        gateway_id = resp.get("gatewayId", "N/A")
        gateway_arn = resp.get("gatewayArn", "N/A")
        gateway_url = resp.get("gatewayUrl", "N/A")
        print_success(f"Gateway 作成: {gateway_id}")
    except Exception as e:
        if "ConflictException" in str(type(e).__name__) or "already exists" in str(e):
            gateways = agentcore_client.list_gateways()
            for gw in gateways.get("items", []):
                if gw.get("name") == GATEWAY_NAME:
                    gateway_id = gw["gatewayId"]
                    # get_gateway で詳細を取得
                    gw_detail = agentcore_client.get_gateway(gatewayIdentifier=gateway_id)
                    gateway_arn = gw_detail.get("gatewayArn", f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:gateway/{gateway_id}")
                    gateway_url = gw_detail.get("gatewayUrl", "N/A")
                    break
            print_success(f"Gateway 既存（スキップ）: {gateway_id}")
            # allowedClients を現在のクライアントに更新
            print_info("アクション", "Gateway authorizer を現在の Cognito に更新中...")
            agentcore_client.update_gateway(
                gatewayIdentifier=gateway_id,
                name=GATEWAY_NAME,
                protocolType="MCP",
                authorizerType="CUSTOM_JWT",
                authorizerConfiguration={
                    "customJWTAuthorizer": {
                        "discoveryUrl": discovery_url,
                        "allowedClients": [client_id_2lo, client_id_3lo],
                    }
                },
                roleArn=gateway_role_arn,
                policyEngineConfiguration={
                    "mode": "ENFORCE",
                    "arn": policy_engine_arn,
                },
            )
            print_success("Gateway authorizer 更新完了")
        else:
            raise
    print_info("Gateway ID", gateway_id)
    print_info("Gateway ARN", gateway_arn)
    print_info("Gateway URL", gateway_url)

    # READY になるまで待機
    wait_for_status(
        agentcore_client,
        lambda: agentcore_client.get_gateway(gatewayIdentifier=gateway_id),
        ["READY", "ACTIVE"],
        "Gateway",
    )
    print_end()

    # =========================================================================
    # Step 9: Gateway Target (Lambda)
    # =========================================================================
    print_step(9, "Gateway Target (Lambda) 作成")

    tool_schema = [
        {
            "name": "process_refund",
            "description": "返金処理を実行する。指定された注文に対して返金を行う。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "注文ID"},
                    "amount": {"type": "number", "description": "返金額（USD）"},
                    "reason": {"type": "string", "description": "返金理由"},
                },
                "required": ["order_id", "amount"],
            },
        },
        {
            "name": "get_order_status",
            "description": "注文のステータスを確認する。配送状況や追跡番号を返す。",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "注文ID"},
                },
                "required": ["order_id"],
            },
        },
    ]

    try:
        resp = agentcore_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name="handson-tools",
            description="ハンズオン用ツール（返金処理 + 注文確認）",
            credentialProviderConfigurations=[
                {
                    "credentialProviderType": "GATEWAY_IAM_ROLE",
                }
            ],
            targetConfiguration={
                "mcp": {
                    "lambda": {
                        "lambdaArn": lambda_arn,
                        "toolSchema": {
                            "inlinePayload": tool_schema,
                        },
                    }
                }
            },
        )
        target_id = resp.get("targetId", "N/A")
        print_success(f"Gateway Target 作成: {target_id}")
    except Exception as e:
        if "ConflictException" in str(type(e).__name__) or "already exists" in str(e):
            targets = agentcore_client.list_gateway_targets(gatewayIdentifier=gateway_id)
            for t in targets.get("items", []):
                if t.get("name") == "handson-tools":
                    target_id = t["targetId"]
                    break
            print_success(f"Gateway Target 既存（スキップ）: {target_id}")
        else:
            raise
    print_info("Target ID", target_id)

    # READY になるまで待機
    wait_for_status(
        agentcore_client,
        lambda: agentcore_client.get_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target_id
        ),
        ["READY", "ACTIVE"],
        "Gateway Target",
    )
    print_end()

    # =========================================================================
    # Step 10: Cedar Policy
    # =========================================================================
    print_step(10, "Cedar Policy 作成")

    # Policy 1: get_order_status は誰でも許可
    cedar_allow_read = f"""permit(
    principal,
    action == AgentCore::Action::"handson-tools___get_order_status",
    resource == AgentCore::Gateway::"{gateway_arn}"
);"""

    # Policy 2: process_refund は 500 未満のみ許可
    cedar_refund_limit = f"""permit(
    principal,
    action == AgentCore::Action::"handson-tools___process_refund",
    resource == AgentCore::Gateway::"{gateway_arn}"
) when {{
    context.input.amount < 500
}};"""

    print_info("Policy 1", "get_order_status: 全ユーザーに許可")
    print_info("Policy 2", "process_refund: 500 USD 未満のみ許可")

    # Policy 1 作成
    try:
        resp1 = agentcore_client.create_policy(
            name="allow_order_status",
            description="注文ステータス確認は全ユーザーに許可",
            policyEngineId=policy_engine_id,
            definition={"cedar": {"statement": cedar_allow_read}},
            enforcementMode="ACTIVE",
        )
        print_success(f"Policy 'allow_order_status' 作成: {resp1.get('policyId', 'N/A')}")
    except Exception as e:
        if "already exists" in str(e) or "Conflict" in str(e):
            print_success("Policy 'allow_order_status' 既存（スキップ）")
        else:
            raise

    # Policy 2 作成
    try:
        resp2 = agentcore_client.create_policy(
            name="limit_refund_amount",
            description="返金は500USD未満のみ許可",
            policyEngineId=policy_engine_id,
            definition={"cedar": {"statement": cedar_refund_limit}},
            enforcementMode="ACTIVE",
        )
        print_success(f"Policy 'limit_refund_amount' 作成: {resp2.get('policyId', 'N/A')}")
    except Exception as e:
        if "already exists" in str(e) or "Conflict" in str(e):
            print_success("Policy 'limit_refund_amount' 既存（スキップ）")
        else:
            raise
    print_end()

    # =========================================================================
    # 設定ファイル保存
    # =========================================================================
    hosted_ui_url = f"https://{domain_name}.auth.{REGION}.amazoncognito.com"
    token_endpoint = f"{hosted_ui_url}/oauth2/token"
    authorize_endpoint = f"{hosted_ui_url}/oauth2/authorize"

    config = {
        "region": REGION,
        "account_id": account_id,
        # Cognito
        "user_pool_id": user_pool_id,
        "domain_name": domain_name,
        "client_id_2lo": client_id_2lo,
        "client_secret_2lo": client_secret_2lo,
        "client_id_3lo": client_id_3lo,
        "client_secret_3lo": client_secret_3lo,
        "username": username,
        "password": password,
        "issuer_url": issuer_url,
        "hosted_ui_url": hosted_ui_url,
        "token_endpoint": token_endpoint,
        "authorize_endpoint": authorize_endpoint,
        # AgentCore Identity
        "callback_url": callback_url,
        "provider_arn": provider_arn,
        "credential_provider_name": CREDENTIAL_PROVIDER_NAME,
        "resource_server_id": RESOURCE_SERVER_ID,
        "scopes_2lo": [f"{RESOURCE_SERVER_ID}/read", f"{RESOURCE_SERVER_ID}/write"],
        "scopes_3lo": ["openid", "profile", "email"],
        # Gateway
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "gateway_url": gateway_url,
        "gateway_role_arn": gateway_role_arn,
        "target_id": target_id,
        # Lambda
        "lambda_arn": lambda_arn,
        "lambda_role_name": LAMBDA_ROLE_NAME,
        # Policy
        "policy_engine_id": policy_engine_id,
        "policy_engine_arn": policy_engine_arn,
    }

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"  📁 設定を {CONFIG_FILE} に保存しました")
    print()
    print(f"  作成されたリソース:")
    print(f"    • Cognito User Pool: {user_pool_id}")
    print(f"    • Gateway: {gateway_url}")
    print(f"    • Policy Engine: {policy_engine_id}")
    print(f"    • Lambda: {LAMBDA_FUNCTION_NAME}")
    print()
    print(f"  次のステップ:")
    print(f"    • 2LO デモ:     python agentcore_identity_2lo.py")
    print(f"    • 3LO デモ:     python agentcore_identity_3lo.py")
    print(f"    • Gateway デモ: python agentcore_gateway_demo.py")
    print(f"    • Policy デモ:  python agentcore_policy_demo.py")
    print()

    print_header("セットアップ完了")


if __name__ == "__main__":
    main()
