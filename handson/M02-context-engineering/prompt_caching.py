"""
モジュール 2: プロンプトキャッシュの実装

Amazon Bedrock のプロンプトキャッシュ機能を使用して、
静的なコンテンツ（システムプロンプト、ツール定義、参照ドキュメント）を
キャッシュし、コストとレイテンシーを削減します。

キャッシュの構造:
1. システムプロンプト（最も静的） ← キャッシュ
2. ツール定義（静的）            ← キャッシュ
3. 参照ドキュメント（準静的）     ← キャッシュ
4. 会話履歴（動的）
5. ユーザー入力（動的）
"""

import boto3
import json
import time

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

# プロンプトキャッシュ対応モデル
MODEL_ID = "us.anthropic.claude-sonnet-4-20250514-v1:0"


# =============================================================================
# デモ 1: システムプロンプトのキャッシュ
# =============================================================================

def demo_system_prompt_caching():
    """システムプロンプトをキャッシュして複数回呼び出し"""

    print("\n" + "─" * 60)
    print("  デモ 1: システムプロンプトのキャッシュ")
    print("─" * 60)

    # 長いシステムプロンプト（キャッシュの効果が出やすい）
    system_prompt = """あなたはエンタープライズ向けカスタマーサポートの専門エージェントです。

## 対応方針
- 常にプロフェッショナルで丁寧な対応を心がける
- 顧客の問題を正確に把握し、具体的な解決策を提示する
- エスカレーションが必要な場合は明確に伝える
- セキュリティに関する情報は決して外部に漏らさない

## 対応カテゴリ
1. 技術サポート: ログイン問題、API エラー、パフォーマンス問題
2. 請求サポート: 料金説明、返金処理、プラン変更
3. 商品サポート: 機能説明、使い方、レコメンデーション

## 回答形式
- 問題の確認
- 原因の説明
- 解決策の提示
- フォローアップの案内

## 制約事項
- 個人情報の取り扱いには最大限の注意を払う
- 確認できない情報は推測で回答しない
- 複雑な問題は担当チームへのエスカレーションを推奨する
- 回答は日本語で行う"""

    # キャッシュチェックポイント付きのシステムプロンプト
    system_content = [
        {"text": system_prompt},
        {"cachePoint": {"type": "default"}}  # ← キャッシュポイント
    ]

    # 複数のユーザーメッセージで呼び出し（キャッシュの効果を確認）
    user_queries = [
        "パスワードをリセットしたいです",
        "今月の請求額が高い理由を教えてください",
        "新しいダッシュボード機能について教えてください",
    ]

    results = []
    for i, query in enumerate(user_queries, 1):
        start_time = time.time()

        response = bedrock.converse(
            modelId=MODEL_ID,
            system=system_content,
            messages=[{"role": "user", "content": [{"text": query}]}],
            inferenceConfig={"maxTokens": 300, "temperature": 0.3}
        )

        elapsed = time.time() - start_time
        usage = response["usage"]

        # キャッシュ使用状況の確認
        cache_read = usage.get("cacheReadInputTokens", 0)
        cache_write = usage.get("cacheWriteInputTokens", 0)

        result = {
            "query": query,
            "input_tokens": usage["inputTokens"],
            "cache_read": cache_read,
            "cache_write": cache_write,
            "latency_ms": round(elapsed * 1000)
        }
        results.append(result)

        print(f"\n  呼び出し {i}: {query}")
        print(f"    入力トークン: {usage['inputTokens']}")
        print(f"    キャッシュ読み取り: {cache_read} tokens")
        print(f"    キャッシュ書き込み: {cache_write} tokens")
        print(f"    レイテンシー: {result['latency_ms']}ms")

    # キャッシュ効果のまとめ
    print(f"\n  [キャッシュ効果]")
    if results[0]["cache_write"] > 0 and results[-1]["cache_read"] > 0:
        print(f"  ✅ 初回: キャッシュ書き込み {results[0]['cache_write']} tokens")
        print(f"  ✅ 2回目以降: キャッシュ読み取り {results[-1]['cache_read']} tokens")
        print(f"  → システムプロンプトの再計算をスキップ")
    else:
        print(f"  ℹ️  キャッシュ統計: write={results[0]['cache_write']}, read={results[-1]['cache_read']}")
        print(f"  (キャッシュはモデルとリクエストパターンに依存します)")


# =============================================================================
# デモ 2: ツール定義のキャッシュ (Strands SDK)
# =============================================================================

def demo_tool_caching():
    """Strands SDK でツール定義をキャッシュ"""

    print("\n" + "─" * 60)
    print("  デモ 2: ツール定義のキャッシュ（Strands SDK）")
    print("─" * 60)

    print("""
    Strands SDK でのツールキャッシュ実装例:

    from strands import Agent, tool
    from strands.models import BedrockModel

    @tool
    def search_knowledge_base(query: str) -> str:
        \"\"\"社内ナレッジベースを検索します\"\"\"
        ...

    @tool
    def check_order_status(order_id: str) -> str:
        \"\"\"注文ステータスを確認します\"\"\"
        ...

    @tool
    def process_refund(order_id: str, amount: float) -> str:
        \"\"\"返金処理を実行します\"\"\"
        ...

    # cache_tools="default" でツール定義をキャッシュ
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        cache_tools="default"  # ← ツールキャッシュ有効化
    )

    agent = Agent(
        model=bedrock_model,
        tools=[search_knowledge_base, check_order_status, process_refund]
    )

    効果:
    - ツール定義のトークン（通常 500～2000 tokens）をキャッシュ
    - 2回目以降の呼び出しでコスト ~90% 削減（キャッシュ部分）
    - レイテンシーも改善
    """)


# =============================================================================
# デモ 3: 参照ドキュメントのキャッシュ
# =============================================================================

def demo_document_caching():
    """大きな参照ドキュメントをキャッシュ"""

    print("\n" + "─" * 60)
    print("  デモ 3: 参照ドキュメントのキャッシュ")
    print("─" * 60)

    # 大きなドキュメント（FAQ、ポリシーなど）
    reference_doc = """
    === カスタマーサポートポリシー v3.2 ===

    第1章: 返金ポリシー
    - 購入後30日以内: 全額返金
    - 購入後31-90日: 50%返金
    - 購入後91日以降: 返金不可
    - デジタル商品: ダウンロード前のみ返金可
    - サブスクリプション: 日割り計算で返金

    第2章: エスカレーション基準
    - 金額が10万円を超える案件: マネージャー承認必須
    - セキュリティインシデント: 即時セキュリティチームへ
    - 法的リスクを含む案件: 法務チームへ
    - VIP顧客（年間利用額500万円以上）: 専任担当者へ

    第3章: SLA
    - 初回応答: 1時間以内
    - 解決目標: 24時間以内
    - エスカレーション後: 4時間以内に更新
    - 重大インシデント: 30分以内に対応開始

    第4章: コミュニケーションガイドライン
    - 敬語を使用する
    - 専門用語を避け、分かりやすい表現を使う
    - 解決策は箇条書きで提示する
    - フォローアップの連絡先を必ず案内する
    """ * 3  # ドキュメントを大きくしてキャッシュの効果を出す

    # ドキュメントをキャッシュポイント付きで送信
    messages_with_cache = [
        {
            "role": "user",
            "content": [
                {
                    "text": f"以下のポリシードキュメントを参照して回答してください:\n\n{reference_doc}"
                },
                {"cachePoint": {"type": "default"}},  # ← ドキュメント後にキャッシュ
                {
                    "text": "質問: 購入後45日の商品の返金ポリシーを教えてください"
                }
            ]
        }
    ]

    print(f"  参照ドキュメントサイズ: {len(reference_doc)} 文字")
    print(f"  キャッシュポイント: ドキュメント直後に設定")

    start_time = time.time()
    response = bedrock.converse(
        modelId=MODEL_ID,
        messages=messages_with_cache,
        inferenceConfig={"maxTokens": 300, "temperature": 0.1}
    )
    elapsed = time.time() - start_time
    usage = response["usage"]

    print(f"\n  結果:")
    print(f"    入力トークン: {usage['inputTokens']}")
    print(f"    キャッシュ書き込み: {usage.get('cacheWriteInputTokens', 0)}")
    print(f"    レイテンシー: {round(elapsed * 1000)}ms")
    print(f"    回答: {response['output']['message']['content'][0]['text'][:200]}...")

    # 2回目の呼び出し（別の質問、同じドキュメント）
    messages_with_cache_2 = [
        {
            "role": "user",
            "content": [
                {
                    "text": f"以下のポリシードキュメントを参照して回答してください:\n\n{reference_doc}"
                },
                {"cachePoint": {"type": "default"}},
                {
                    "text": "質問: VIP顧客の定義と特別対応について教えてください"
                }
            ]
        }
    ]

    start_time = time.time()
    response2 = bedrock.converse(
        modelId=MODEL_ID,
        messages=messages_with_cache_2,
        inferenceConfig={"maxTokens": 300, "temperature": 0.1}
    )
    elapsed2 = time.time() - start_time
    usage2 = response2["usage"]

    print(f"\n  2回目（キャッシュヒット期待）:")
    print(f"    入力トークン: {usage2['inputTokens']}")
    print(f"    キャッシュ読み取り: {usage2.get('cacheReadInputTokens', 0)}")
    print(f"    レイテンシー: {round(elapsed2 * 1000)}ms")
    print(f"    回答: {response2['output']['message']['content'][0]['text'][:200]}...")


# =============================================================================
# メイン実行
# =============================================================================

def run_prompt_caching_demo():
    """プロンプトキャッシュデモの全体実行"""

    print("=" * 70)
    print(" プロンプトキャッシュ: コストとレイテンシーの最適化")
    print("=" * 70)
    print("""
    プロンプトキャッシュの仕組み:
    - cachePoint マーカーを挿入してキャッシュ境界を指定
    - 初回: キャッシュに書き込み（通常料金 + 少額の書き込みコスト）
    - 2回目以降: キャッシュから読み取り（大幅なコスト削減）
    - TTL 内に再利用しないとキャッシュは無効化される
    """)

    demo_system_prompt_caching()
    demo_tool_caching()
    demo_document_caching()

    # まとめ
    print(f"\n{'─' * 70}")
    print("  [まとめ] プロンプトキャッシュのベストプラクティス")
    print(f"{'─' * 70}")
    print("""
    1. キャッシュに適したコンテンツの配置順序:
       静的 → 準静的 → 動的 の順にプロンプトを構成

    2. キャッシュの最小サイズ要件:
       - Claude: 1024 tokens 以上が推奨
       - 短すぎるプロンプトではキャッシュのオーバーヘッドが逆効果

    3. モデルごとの対応状況:
       - Claude Sonnet 4: ✅ 対応
       - Claude Haiku: ✅ 対応
       - Nova Pro/Lite: ❌ 非対応（2026年8月時点）

    4. コスト削減の目安:
       - キャッシュ書き込み: 通常の入力トークン料金の 1.25倍
       - キャッシュ読み取り: 通常の入力トークン料金の 0.1倍（90% 削減）
    """)


if __name__ == "__main__":
    run_prompt_caching_demo()
