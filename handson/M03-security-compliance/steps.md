# モジュール 3: セキュリティとコンプライアンスの実装 - ハンズオン手順

## パート 1: AgentCore Identity - 認証と認可（15分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M03-security-compliance
```

### ステップ 1.2: フルセットアップの実行

以下のリソースを一括作成し、Identity（認証）と Policy（認可）のデモ基盤を構築します:

**[Identity 基盤]**
- Cognito User Pool + ドメイン + Resource Server（OAuth 2.0 認可サーバー）
- App Client（2LO: `client_credentials` / 3LO: `code` フロー）
- テストユーザー
- AgentCore OAuth2 Credential Provider

**[Gateway + Policy 基盤]**
- モック Lambda 関数（`process_refund` / `get_order_status`）
- Gateway 用 IAM ロール
- AgentCore Gateway（JWT Authorizer + Policy Engine 付き）
- Gateway Target（Lambda）
- Policy Engine + Cedar ポリシー

```bash
python agentcore_identity_setup.py
```

> ⏳ Gateway や Policy Engine の作成に数分かかります。  
> 設定情報は `identity_config.json` に保存され、後続のデモで使用されます。  
> 2回目以降の実行では既存リソースがスキップされます（冪等）。

### ステップ 1.3: 2LO (Client Credentials) デモ

ユーザーの介在なしにエージェント自身の権限でトークンを取得する M2M フローです。

```bash
python agentcore_identity_2lo.py
```

確認ポイント:
- Client ID + Secret だけでトークンを取得できる
- JWT ペイロードに `sub`（アプリケーション自身）と `scope`（カスタムスコープ）が含まれる
- ユーザーの同意やログインが一切不要

### ステップ 1.4: 3LO (Authorization Code) デモ

ユーザーの同意を得て、エージェントがユーザーの代理でリソースにアクセスするフローです。

```bash
python agentcore_identity_3lo.py
```

確認ポイント:
- 認可 URL が生成される（本番: ユーザーが Hosted UI でログイン＆同意）
- `y` を入力してユーザー同意をシミュレート
- ID Token にユーザー情報（email、username）が含まれる
- Access Token で「誰の代理で動作しているか」が明確になる

### ステップ 1.5: Gateway 認証デモ

Strands Agent が Gateway に MCP 接続し、JWT 認証の通過/拒否を確認します。

```bash
python agentcore_gateway_demo.py
```

確認ポイント:
- **有効なトークン** → Gateway 認証通過 → Lambda 実行 → 応答返却
- **無効なトークン** → JWT Authorizer で即座に 403 ブロック

### ステップ 1.6: 2LO vs 3LO 比較

| 観点 | 2LO (Client Credentials) | 3LO (Authorization Code) |
|------|-------------------------|--------------------------|
| ユーザー同意 | 不要 | 必須 |
| トークン主体 | アプリケーション自身 | ユーザー |
| ID Token | なし | あり（ユーザー情報） |
| スコープ | カスタムスコープのみ | openid/profile/email |
| ユースケース | M2M、バッチ処理 | ユーザー代理動作 |

### ステップ 1.7: AgentCore Identity アーキテクチャの理解

**認証フローの方向:**
- **インバウンド認証**: ユーザー → AgentCore Gateway（JWT Token）
- **アウトバウンド認証**: AgentCore Gateway → ツール/リソース（IAM Role）

**AgentCore Gateway のターゲット別認証:**

| ターゲット種類 | 認証方式 | ユースケース |
|-------------|---------|-------------|
| AWS Lambda | IAM (Gateway Role) | AWS 内部リソースへのアクセス |
| MCP サーバー | OAuth トークン | 外部 MCP ツールへのアクセス |
| OpenAPI | IAM | REST API へのアクセス |
| Smithy | IAM | AWS スタイルの API |

---

## パート 2: AgentCore Policy - Cedar によるアクセス制御（10分）

### ステップ 2.1: Cedar ポリシーデモの実行

Strands Agent が Gateway 経由でツールを呼び出し、Cedar ポリシーによるリアルタイム認可を体験します。

```bash
python agentcore_policy_demo.py
```

**テスト内容:**

| テスト | ツール | 入力 | 期待結果 | 理由 |
|--------|--------|------|----------|------|
| 1 | get_order_status | order_id="ORD-12345" | ✅ ALLOW | 全ユーザーに許可 |
| 2 | process_refund | amount=100 | ✅ ALLOW | 100 < 500 |
| 3 | process_refund | amount=1000 | 🚫 DENY | 1000 >= 500 |

確認ポイント:
- テスト 1, 2: エージェントがツールを実行し、Lambda の結果が返る
- テスト 3: `Tool Execution Denied: Tool call not allowed due to policy enforcement` が返る
- Cedar ポリシーが `context.input.amount` の値でリアルタイムに判断している

### ステップ 2.2: Cedar ポリシーの構文理解

セットアップで作成された実際のポリシー:

```cedar
// Policy 1: 注文ステータス確認は全ユーザーに許可
permit(
    principal,
    action == AgentCore::Action::"handson-tools___get_order_status",
    resource == AgentCore::Gateway::"<gateway-arn>"
);

// Policy 2: 返金は 500 USD 未満のみ許可
permit(
    principal,
    action == AgentCore::Action::"handson-tools___process_refund",
    resource == AgentCore::Gateway::"<gateway-arn>"
) when {
    context.input.amount < 500
};
```

**Cedar ポリシーの構成要素:**

| 要素 | 説明 | 今回の例 |
|------|------|---------|
| 効果 | `permit` or `forbid` | `permit` |
| principal | 誰が（JWT の sub クレーム） | 全ユーザー（制約なし） |
| action | 何を（ツール名） | `handson-tools___process_refund` |
| resource | どこに対して（Gateway ARN） | このGateway |
| when | 条件 | `context.input.amount < 500` |

**重要**: ENFORCE モードでは、**明示的に permit されていないアクションは全て deny** されます（deny by default）。

---

## パート 3: Bedrock Guardrails の作成（コンソール操作）（15分）

### ステップ 3.1: Guardrails コンソールを開く

1. AWS コンソールで **Amazon Bedrock** を開く: https://console.aws.amazon.com/bedrock/
2. 左ナビゲーションペインで **Guardrails** を選択
3. **Create guardrail** をクリック

### ステップ 3.2: ガードレール詳細の設定

**Provide guardrail details** ページで以下を入力：

1. **Name**: `agentic-security-guardrail`
2. **Description**: `エージェンティック AI システム向けセキュリティガードレール`
3. **Messaging for blocked prompts**: `申し訳ありませんが、このリクエストにはお答えできません。別のご質問をお願いします。`
4. **Apply the same blocked message for responses** にチェック
5. **Cross-Region inference**（クロスリージョン推論）を展開：
   - **Enable cross-Region inference for your guardrail** にチェックを入れる
   - ガードレールプロファイルを選択（日本語対応に必要）
6. **Next** をクリック

### ステップ 3.3: コンテンツフィルターの設定

**Configure content filters** ページで以下を設定：

1. **フィルターティア**: **Standard** を選択（日本語テキストのフィルタリングに必要）
2. **Enable harmful content filters** を ON にする
2. 以下のカテゴリすべてで Input/Output 両方の強度を **High** に設定：

   | カテゴリ | Input Strength | Output Strength |
   |---------|---------------|-----------------|
   | Hate | High | High |
   | Insults | High | High |
   | Sexual | High | High |
   | Violence | High | High |
   | Misconduct | High | High |

3. **Enable prompt attacks filter** を ON にする
4. **Next** をクリック

### ステップ 3.4: 拒否トピックの設定

**Add denied topics** ページで以下のトピックを追加：

**トピック 1: 投資助言**
1. **Add denied topic** をクリック
2. **Name**: `investment_advice`
3. **Definition**: `特定の株式や投資商品の購入推奨、金融投資のアドバイス`
4. **Add sample phrases** に以下を入力：
   - `この株を買うべきですか？`
   - `今は投資のタイミングですか？`
5. **Confirm** をクリック

**トピック 2: 医療診断**
1. **Add denied topic** をクリック
2. **Name**: `medical_diagnosis`
3. **Definition**: `医療診断、処方箋の推奨、治療方法の指示`
4. **Add sample phrases** に以下を入力：
   - `この症状は何の病気ですか？`
   - `この薬を飲むべきですか？`
5. **Confirm** をクリック
6. **Next** をクリック

### ステップ 3.5: 機密情報フィルターの設定

**Add sensitive information filters** ページで以下を設定：

**PII types（個人識別情報）**:

1. **Add PII type** をクリックし、以下を追加：

   | PII タイプ | アクション |
   |-----------|----------|
   | Email | Anonymize (マスク) |
   | Phone | Anonymize (マスク) |
   | Name | Anonymize (マスク) |
   | Credit/Debit Card Number | Block (ブロック) |
   | Address | Anonymize (マスク) |

2. **Regex patterns（カスタム正規表現）**:
   - **Add regex** をクリック
   - **Name**: `Japanese Phone Number`
   - **Regex pattern**: `0\d{1,4}-\d{1,4}-\d{4}`
   - **Action**: Anonymize
   - **Confirm** をクリック

3. **Next** をクリック

### ステップ 3.6: ワードフィルターの設定（オプション）

**Add word filters** ページ：
- 必要に応じてカスタムワードを追加（今回はスキップ可）
- **Next** をクリック

### ステップ 3.7: Contextual Grounding（オプション）

- 今回はスキップ
- **Next** をクリック

### ステップ 3.8: 確認と作成

1. **Review and create** ページで設定内容を確認
2. **Create guardrail** をクリック
3. 作成完了後、Guardrail ID をメモ

### ステップ 3.9: Guardrails のテスト（コンソール）

作成した Guardrail の詳細ページで：

1. **Working draft** を選択
2. 画面右側の **Test** パネルを使用
3. **Select model** でテスト用モデルを選択（Amazon Nova Pro 等）
4. 以下のテストプロンプトを入力して **Run** をクリック：

**テスト 1: PII 検出**
```
田中太郎さんの連絡先は tanaka@example.com で、電話番号は 03-1234-5678 です。
```
→ メールアドレスと電話番号がマスクされることを確認

**テスト 2: クレジットカード番号のブロック**
```
カード番号 4111-1111-1111-1111 で支払いを処理してください。
```
→ ブロックされることを確認

**テスト 3: 禁止トピック**
```
今買うべき株を教えてください。投資のタイミングはいつですか？
```
→ 禁止トピックとしてブロックされることを確認

**テスト 4: 通常のリクエスト（通過すべき）**
```
注文 ORD-12345 のステータスを確認してください。
```
→ 問題なく通過することを確認

### ステップ 3.10: Guardrail のバージョン作成

本番環境で使用するために、バージョンを作成します：

1. 作成した Guardrail の詳細ページを開く
2. **Versions** セクションで **Create version** をクリック
3. **Description**: `v1 - Initial production version`
4. **Create version** をクリック

---

## パート 4: 監査ログの実装（5分）

### ステップ 4.1: 監査ログデモの実行

```bash
python audit_logging.py
```

出力を確認し、エージェンティック AI の監査証跡の構造を理解します。

### ステップ 4.2: CloudWatch Logs での確認（コンソール）

1. AWS コンソールで **CloudWatch** を開く
2. 左メニューから **Log groups** を選択
3. `/agentic-ai/audit-logs` ロググループを選択
4. 最新のログストリームを開き、監査イベントを確認

各イベントには以下が記録されています：
- `event_type`: SESSION_START / TOOL_INVOCATION / GUARDRAIL_INTERVENTION / SESSION_END
- `policy_decision`: ALLOW / DENY
- `result`: SUCCESS / BLOCKED

### ステップ 4.3: CloudWatch Logs Insights でクエリ

1. CloudWatch コンソールで **Logs Insights** を選択
2. ロググループに `/agentic-ai/audit-logs` を選択
3. 以下のクエリを実行：

```
fields @timestamp, event_type, action, policy_decision, result
| filter event_type = "TOOL_INVOCATION"
| sort @timestamp desc
| limit 20
```

---

## パート 5: ディスカッション（5分）

### エージェンティック AI の多層防御

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Identity (AuthN)                        │  → AgentCore Identity
├─────────────────────────────────────────────────┤
│ Layer 2: Policy (AuthZ)                          │  → AgentCore Policy (Cedar)
├─────────────────────────────────────────────────┤
│ Layer 3: Content Safety                          │  → Bedrock Guardrails
├─────────────────────────────────────────────────┤
│ Layer 4: Network Isolation                       │  → VPC / PrivateLink
├─────────────────────────────────────────────────┤
│ Layer 5: Audit & Monitoring                      │  → CloudTrail / CloudWatch
└─────────────────────────────────────────────────┘
```

### 4 つの自律レベルとセキュリティ要件

| レベル | 説明 | セキュリティ要件 |
|-------|------|----------------|
| No Agency | 人間主導 | 標準認証 |
| Prescribed Agency | 明示的な承認が必要 | 承認ワークフロー |
| Supervised Agency | 人間がトリガー、自律実行 | Policy + 監査 |
| Full Agency | 完全自律 | 多層防御 + リアルタイム監視 |

---

## 参考ドキュメント

- [Amazon Bedrock Guardrails - 概要](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html)
- [Amazon Bedrock Guardrails - 機密情報フィルターの設定](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-sensitive-filters.html)
- [Amazon Bedrock Guardrails - コンテンツフィルターの設定](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-content-filters-overview.html)
- [Amazon Bedrock Guardrails - バージョンの作成](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-versions-create.html)
- [Amazon Bedrock AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html)
- [Amazon Bedrock AgentCore Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html)
- [Amazon CloudWatch Logs Insights - クエリ構文](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [OWASP Agentic AI Threats](https://owasp.org/www-project-agentic-ai-threats/)
