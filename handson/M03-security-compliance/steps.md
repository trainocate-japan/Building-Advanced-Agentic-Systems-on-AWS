# モジュール 3: セキュリティとコンプライアンスの実装 - ハンズオン手順

## パート 1: AgentCore Identity - 認証と認可（10分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M03-security-compliance
```

### ステップ 1.2: AgentCore Identity の概要確認

```bash
python3.12 agentcore_identity_demo.py
```

出力を確認し、以下のアーキテクチャを理解します：

- **インバウンド認証**: ユーザー → AgentCore Runtime（IAM or OAuth）
- **アウトバウンド認証**: AgentCore Runtime → ツール/リソース（IAM Role or OAuth Token）
- **OAuth 2LO**: エージェント自身のリソースアクセス（M2M）
- **OAuth 3LO**: ユーザーの代理で動作（ユーザー同意が必要）

### ステップ 1.3: AgentCore Gateway の認証方式

| ターゲット種類 | 認証方式 | ユースケース |
|-------------|---------|-------------|
| AWS Lambda | IAM | AWS 内部リソースへのアクセス |
| MCP サーバー | OAuth トークン | 外部 MCP ツールへのアクセス |
| OpenAPI | IAM | REST API へのアクセス |
| Smithy | IAM | AWS スタイルの API |

---

## パート 2: AgentCore Policy - Cedar によるアクセス制御（10分）

### ステップ 2.1: Cedar ポリシーデモの実行

```bash
python3.12 agentcore_policy_demo.py
```

出力を確認し、Cedar ポリシーの認可フローを理解します：
1. JWT トークン受信 → 2. MCP ツールコールリクエスト → 3. Cedar 認可リクエスト → 4. ALLOW/DENY

### ステップ 2.2: Cedar ポリシーの構文理解

```cedar
// 500ドル未満の返金のみ許可（財務部門ユーザー限定）
permit (
    principal,
    action == MCP::Action::"process_refund",
    resource
)
when {
    principal.department == "finance" &&
    resource.amount < 500
};
```

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
5. **Next** をクリック

### ステップ 3.3: コンテンツフィルターの設定

**Configure content filters** ページで以下を設定：

1. **Enable harmful content filters** を ON にする
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
python3.12 audit_logging.py
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
