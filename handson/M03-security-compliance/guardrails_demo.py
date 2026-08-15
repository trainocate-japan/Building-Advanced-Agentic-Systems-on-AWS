"""
モジュール 3: Bedrock Guardrails - コンテンツ保護と PII フィルタリング

Bedrock Guardrails を使用して、エージェントの入出力に対する
コンテンツフィルタリングと PII 保護を実装します。

保護レイヤー:
- コンテンツフィルター: 有害コンテンツのブロック
- PII 検出・マスキング: 個人情報の保護
- トピック制限: 禁止トピックへの応答防止
- ワードフィルター: 特定語句のブロック
"""

import boto3
import json
import time

bedrock = boto3.client("bedrock", region_name="us-east-1")
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

GUARDRAIL_NAME = "agentic-security-guardrail"
MODEL_ID = "us.amazon.nova-pro-v1:0"


# =============================================================================
# Guardrail の作成
# =============================================================================

def create_guardrail():
    """エージェント向け Guardrail を作成"""

    print("\n" + "─" * 70)
    print("  Step 1: Guardrail の作成")
    print("─" * 70)

    try:
        response = bedrock.create_guardrail(
            name=GUARDRAIL_NAME,
            description="エージェンティック AI システム向けセキュリティガードレール",
            # コンテンツフィルター
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                    {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                ]
            },
            # PII フィルター（個人情報保護）
            sensitiveInformationPolicyConfig={
                "piiEntitiesConfig": [
                    {"type": "EMAIL", "action": "ANONYMIZE"},
                    {"type": "PHONE", "action": "ANONYMIZE"},
                    {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
                    {"type": "NAME", "action": "ANONYMIZE"},
                    {"type": "ADDRESS", "action": "ANONYMIZE"},
                ],
                "regexesConfig": [
                    {
                        "name": "Japanese Phone Number",
                        "description": "日本の電話番号をマスク",
                        "pattern": r"0\d{1,4}-\d{1,4}-\d{4}",
                        "action": "ANONYMIZE"
                    },
                    {
                        "name": "Internal Project Code",
                        "description": "社内プロジェクトコードをブロック",
                        "pattern": r"PRJ-[A-Z]{3}-\d{4}",
                        "action": "BLOCK"
                    }
                ]
            },
            # トピック制限
            topicPolicyConfig={
                "topicsConfig": [
                    {
                        "name": "investment_advice",
                        "definition": "特定の株式や投資商品の購入推奨、金融投資のアドバイス",
                        "type": "DENY",
                        "examples": [
                            "この株を買うべきですか？",
                            "今は投資のタイミングですか？"
                        ]
                    },
                    {
                        "name": "medical_diagnosis",
                        "definition": "医療診断、処方箋の推奨、治療方法の指示",
                        "type": "DENY",
                        "examples": [
                            "この症状は何の病気ですか？",
                            "この薬を飲むべきですか？"
                        ]
                    }
                ]
            },
            # ブロック時のメッセージ
            blockedInputMessaging="申し訳ありませんが、このリクエストにはお答えできません。別のご質問をお願いします。",
            blockedOutputsMessaging="申し訳ありませんが、この情報を提供することはできません。",
        )

        guardrail_id = response["guardrailId"]
        version = response["version"]
        print(f"  ✅ Guardrail 作成成功")
        print(f"     ID: {guardrail_id}")
        print(f"     Version: {version}")
        return guardrail_id, version

    except bedrock.exceptions.ConflictException:
        # 既存の Guardrail を取得
        print(f"  ℹ️  既存の Guardrail を使用")
        response = bedrock.list_guardrails()
        for g in response.get("guardrails", []):
            if g["name"] == GUARDRAIL_NAME:
                print(f"     ID: {g['id']}")
                return g["id"], g["version"]
        raise Exception("Guardrail が見つかりません")


# =============================================================================
# Guardrail のテスト
# =============================================================================

def test_guardrail(guardrail_id: str, version: str):
    """Guardrail の各フィルターをテスト"""

    print("\n" + "─" * 70)
    print("  Step 2: Guardrail テスト")
    print("─" * 70)

    test_cases = [
        {
            "category": "PII 検出（メールアドレス）",
            "input": "田中太郎さんの連絡先は tanaka@example.com で、電話番号は 03-1234-5678 です。",
            "expected_action": "ANONYMIZE"
        },
        {
            "category": "PII 検出（クレジットカード）",
            "input": "カード番号 4111-1111-1111-1111 で支払いを処理してください。",
            "expected_action": "BLOCK"
        },
        {
            "category": "禁止トピック（投資助言）",
            "input": "AIの次に来る投資テーマは何ですか？今買うべき株を教えてください。",
            "expected_action": "BLOCK"
        },
        {
            "category": "通常のリクエスト（許可）",
            "input": "注文 ORD-12345 のステータスを確認してください。",
            "expected_action": "NONE"
        },
        {
            "category": "社内プロジェクトコード（カスタム正規表現）",
            "input": "PRJ-SEC-2026 プロジェクトの詳細を教えてください。",
            "expected_action": "BLOCK"
        },
    ]

    for tc in test_cases:
        print(f"\n  [{tc['category']}]")
        print(f"  入力: {tc['input']}")

        try:
            response = bedrock_runtime.converse(
                modelId=MODEL_ID,
                messages=[{"role": "user", "content": [{"text": tc["input"]}]}],
                guardrailConfig={
                    "guardrailIdentifier": guardrail_id,
                    "guardrailVersion": version
                },
                inferenceConfig={"maxTokens": 300}
            )

            # Guardrail の介入結果を確認
            stop_reason = response.get("stopReason", "")
            output_text = response["output"]["message"]["content"][0]["text"]

            if stop_reason == "guardrail_intervened":
                print(f"  🛡️  Guardrail 介入: コンテンツがブロック/マスクされました")
                print(f"  出力: {output_text[:200]}")

                # トレース情報の確認
                trace = response.get("trace", {}).get("guardrail", {})
                if trace:
                    print(f"  トレース: {json.dumps(trace, ensure_ascii=False)[:300]}")
            else:
                print(f"  ✅ 通過（フィルターなし）")
                print(f"  出力: {output_text[:200]}")

        except Exception as e:
            print(f"  ⚠️  エラー: {str(e)[:200]}")


# =============================================================================
# Strands エージェントとの統合
# =============================================================================

def demo_strands_guardrail_integration():
    """Strands SDK エージェントに Guardrail を統合する方法"""

    print("\n" + "─" * 70)
    print("  Step 3: Strands SDK との統合（参考）")
    print("─" * 70)

    print("""
    Strands エージェントに Guardrail を統合する実装例:

    from strands import Agent
    from strands.models import BedrockModel

    # Guardrail 設定付きモデル
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        guardrail_config={
            "guardrailIdentifier": "<GUARDRAIL_ID>",
            "guardrailVersion": "DRAFT"
        }
    )

    # エージェント作成
    agent = Agent(
        model=model,
        system_prompt="あなたはカスタマーサポートエージェントです。"
    )

    # 入出力の両方で Guardrail が自動適用される
    response = agent("顧客の連絡先を教えてください")
    # → PII がマスクされた回答が返る

    適用タイミング:
    ┌──────────┐    ┌───────────┐    ┌──────────┐    ┌───────────┐
    │  入力    │───▶│ Guardrail │───▶│  LLM    │───▶│ Guardrail │──▶ 出力
    │          │    │ (入力側)   │    │ 推論    │    │ (出力側)   │
    └──────────┘    └───────────┘    └──────────┘    └───────────┘
    """)


# =============================================================================
# メイン実行
# =============================================================================

def run_guardrails_demo():
    """Guardrails デモの全体実行"""

    print("=" * 70)
    print(" Bedrock Guardrails: エージェントのコンテンツ保護")
    print("=" * 70)

    # Guardrail の作成
    guardrail_id, version = create_guardrail()

    # テスト実行
    test_guardrail(guardrail_id, version)

    # Strands 統合デモ
    demo_strands_guardrail_integration()

    # まとめ
    print("\n" + "=" * 70)
    print(" Guardrails デモ完了")
    print("=" * 70)
    print("\n[Key Takeaways]")
    print("1. Guardrails は入力側と出力側の両方で適用される")
    print("2. PII は ANONYMIZE（マスク）または BLOCK（完全ブロック）を選択可能")
    print("3. トピック制限で業務外の質問を拒否できる")
    print("4. カスタム正規表現で組織固有のパターンを検出可能")
    print("5. エージェントフレームワーク（Strands）と透過的に統合可能")
    print(f"\n  ⚠️  クリーンアップ: cleanup_all.sh で Guardrail を削除します")


if __name__ == "__main__":
    run_guardrails_demo()
