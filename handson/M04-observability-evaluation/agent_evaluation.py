"""
モジュール 4: エージェント評価フレームワーク

AgentCore Evaluations を使用して、エージェントの品質を
組み込みエバリュエーターとカスタムエバリュエーターで評価します。

3 ステージ評価モデル:
1. 計測 (Measure): メトリクス収集
2. 判断 (Judge): スコアリング
3. インサイト (Insight): 改善点の特定
"""

import boto3
import json
import time
from datetime import datetime

bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "us.amazon.nova-pro-v1:0"


# =============================================================================
# 評価データセットの読み込み
# =============================================================================

def load_evaluation_dataset(filepath: str = "evaluation-dataset.jsonl") -> list:
    """評価データセットを読み込み"""
    dataset = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
    except FileNotFoundError:
        # デフォルトデータセットを使用
        dataset = get_default_dataset()
    return dataset


def get_default_dataset() -> list:
    """デフォルトの評価データセット"""
    return [
        {
            "prompt": "注文 ORD-12345 の配送状況を教えてください",
            "referenceResponse": "注文の配送状況を確認し、具体的な配送日と追跡番号を提供する",
            "category": "order_inquiry"
        },
        {
            "prompt": "先月の請求が二重になっている気がします。確認して返金してください。",
            "referenceResponse": "請求履歴を確認し、二重請求があれば返金処理を案内する。金額と処理期間を明示する。",
            "category": "billing_dispute"
        },
        {
            "prompt": "APIのレート制限に頻繁に引っかかります。エンタープライズプランへのアップグレードを検討していますが、コストパフォーマンスを比較してください。",
            "referenceResponse": "現在のプランのレート制限を説明し、エンタープライズプランの特徴とコストを比較。ROI の観点から推奨を提示する。",
            "category": "plan_upgrade"
        },
        {
            "prompt": "機密データの取り扱いポリシーについて教えてください。GDPRに準拠していますか？",
            "referenceResponse": "データ保護ポリシーの概要を説明し、GDPR 準拠状況を明確に回答する。具体的な保護措置を列挙する。",
            "category": "compliance"
        },
        {
            "prompt": "こんにちは",
            "referenceResponse": "丁寧な挨拶と、どのようなサポートが可能かを案内する",
            "category": "greeting"
        },
    ]


# =============================================================================
# 組み込みエバリュエーター
# =============================================================================

def evaluate_helpfulness(query: str, response: str, expected: str) -> dict:
    """有用性を評価（LLM as a Judge）"""

    eval_prompt = f"""以下のカスタマーサポートの回答を「有用性」の観点で1-5のスコアで評価してください。

[ユーザーの質問]
{query}

[エージェントの回答]
{response}

[期待される回答の方向性]
{expected}

評価基準:
5: 非常に有用。質問に完全に答え、追加の有用な情報も提供している
4: 有用。質問に適切に答えている
3: 部分的に有用。回答はあるが不完全
2: あまり有用でない。的外れな部分が多い
1: 有用でない。質問に答えていない

JSON形式で回答してください:
{{"score": <1-5>, "reason": "<理由>"}}"""

    result = bedrock_runtime.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": eval_prompt}]}],
        inferenceConfig={"maxTokens": 200, "temperature": 0.1}
    )

    try:
        eval_text = result["output"]["message"]["content"][0]["text"]
        # JSON を抽出
        import re
        json_match = re.search(r'\{.*\}', eval_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, IndexError):
        pass

    return {"score": 3, "reason": "評価の解析に失敗"}


def evaluate_faithfulness(response: str) -> dict:
    """忠実性（ハルシネーション検出）を評価"""

    eval_prompt = f"""以下の回答に事実と異なる情報（ハルシネーション）が含まれていないか評価してください。

[回答]
{response}

評価基準:
5: 確認可能な事実のみ述べている。推測がある場合は明示している
4: ほぼ正確。小さな不確実性があるが問題ない
3: 一部に検証困難な情報がある
2: いくつかのハルシネーションの可能性がある
1: 明らかに事実と異なる情報を含む

JSON形式で回答: {{"score": <1-5>, "reason": "<理由>"}}"""

    result = bedrock_runtime.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": eval_prompt}]}],
        inferenceConfig={"maxTokens": 200, "temperature": 0.1}
    )

    try:
        eval_text = result["output"]["message"]["content"][0]["text"]
        import re
        json_match = re.search(r'\{.*\}', eval_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, IndexError):
        pass

    return {"score": 3, "reason": "評価の解析に失敗"}


# =============================================================================
# カスタムエバリュエーター
# =============================================================================

def evaluate_custom_disclaimer(response: str) -> dict:
    """カスタム: 免責事項チェック（金融サービス向け）"""

    # プログラマティック評価: 特定のキーワードの存在確認
    disclaimer_keywords = ["ご注意", "免責", "保証するものではありません", "自己責任", "リスク"]
    found = any(kw in response for kw in disclaimer_keywords)

    return {
        "score": 1 if found else 0,
        "type": "binary",
        "reason": "免責事項あり" if found else "免責事項なし（金融関連の場合は要追加）"
    }


def evaluate_custom_response_structure(response: str) -> dict:
    """カスタム: 回答構造チェック"""

    checks = {
        "greeting": any(w in response for w in ["承知", "確認", "ありがとう"]),
        "solution": len(response) > 100,
        "next_steps": any(w in response for w in ["次に", "ステップ", "手順", "ご不明"]),
    }

    score = sum(checks.values()) / len(checks) * 5
    return {
        "score": round(score, 1),
        "checks": checks,
        "reason": f"構造チェック: {sum(checks.values())}/{len(checks)} 項目パス"
    }


# =============================================================================
# 評価実行
# =============================================================================

def run_evaluation():
    """エージェント評価を実行"""

    print("=" * 70)
    print(" エージェント評価フレームワーク")
    print("=" * 70)

    # データセット読み込み
    dataset = load_evaluation_dataset()
    print(f"\n  評価データセット: {len(dataset)} 件")

    # エージェント応答を生成（デモ用に直接 LLM 呼び出し）
    print(f"\n{'─' * 70}")
    print("  [Phase 1] エージェント応答の生成 & 評価")
    print(f"{'─' * 70}")

    all_results = []

    for i, item in enumerate(dataset, 1):
        print(f"\n  ── テストケース {i}/{len(dataset)} ──")
        print(f"  入力: {item['prompt']}")
        print(f"  カテゴリ: {item['category']}")

        # エージェント応答を生成
        response = bedrock_runtime.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": item["prompt"]}]}],
            system=[{"text": "あなたはプロフェッショナルなカスタマーサポートエージェントです。丁寧で具体的な回答を提供してください。"}],
            inferenceConfig={"maxTokens": 500, "temperature": 0.3}
        )
        agent_response = response["output"]["message"]["content"][0]["text"]
        print(f"  応答: {agent_response[:150]}...")

        # 評価実行
        helpfulness = evaluate_helpfulness(item["prompt"], agent_response, item["referenceResponse"])
        faithfulness = evaluate_faithfulness(agent_response)
        disclaimer = evaluate_custom_disclaimer(agent_response)
        structure = evaluate_custom_response_structure(agent_response)

        result = {
            "test_case": i,
            "category": item["category"],
            "helpfulness": helpfulness,
            "faithfulness": faithfulness,
            "disclaimer": disclaimer,
            "structure": structure,
        }
        all_results.append(result)

        print(f"  評価結果:")
        print(f"    Helpfulness: {helpfulness['score']}/5 ({helpfulness.get('reason', '')[:50]})")
        print(f"    Faithfulness: {faithfulness['score']}/5")
        print(f"    Structure: {structure['score']}/5")

    # 集計結果
    print(f"\n{'─' * 70}")
    print("  [Phase 2] 評価結果サマリー")
    print(f"{'─' * 70}")

    avg_helpfulness = sum(r["helpfulness"]["score"] for r in all_results) / len(all_results)
    avg_faithfulness = sum(r["faithfulness"]["score"] for r in all_results) / len(all_results)
    avg_structure = sum(r["structure"]["score"] for r in all_results) / len(all_results)

    print(f"""
    ┌───────────────────────────────────────────────────────────────┐
    │ エバリュエーター       │ 平均スコア  │ 閾値   │ 判定         │
    ├───────────────────────────────────────────────────────────────┤
    │ Helpfulness (有用性)  │  {avg_helpfulness:.1f}/5     │ 4.0   │ {"✅ PASS" if avg_helpfulness >= 4.0 else "❌ FAIL"}     │
    │ Faithfulness (忠実性) │  {avg_faithfulness:.1f}/5     │ 4.0   │ {"✅ PASS" if avg_faithfulness >= 4.0 else "❌ FAIL"}     │
    │ Structure (構造)      │  {avg_structure:.1f}/5     │ 3.5   │ {"✅ PASS" if avg_structure >= 3.5 else "❌ FAIL"}     │
    └───────────────────────────────────────────────────────────────┘
    """)

    # カテゴリ別分析
    print("  [カテゴリ別 Helpfulness]")
    categories = set(r["category"] for r in all_results)
    for cat in sorted(categories):
        cat_results = [r for r in all_results if r["category"] == cat]
        avg = sum(r["helpfulness"]["score"] for r in cat_results) / len(cat_results)
        bar = "█" * int(avg) + "░" * (5 - int(avg))
        print(f"    {cat:20s} {bar} {avg:.1f}/5")

    # 改善提案
    print(f"\n{'─' * 70}")
    print("  [Phase 3] 改善インサイト")
    print(f"{'─' * 70}")
    print("""
    推奨アクション:
    1. 低スコアのカテゴリのシステムプロンプトを改善
    2. 失敗ケースを評価データセットに追加
    3. ツール呼び出しの精度を向上（Tool Selection エバリュエーター追加）
    4. 本番トラフィックからの継続的な評価パイプライン構築
    """)


if __name__ == "__main__":
    run_evaluation()
    print("\n" + "=" * 70)
    print(" エージェント評価デモ完了")
    print("=" * 70)
