"""
モジュール 1: Graph パターン - 条件分岐を含むカスタマーサポート

Strands Agents SDK の Graph パターンを使用して、
条件分岐を含む構造化されたフローチャート型のオーケストレーションを実装します。

Graph の特徴:
- GraphBuilder で宣言的にグラフを構築
- ノードはエージェント（条件分岐も可能）
- エッジで依存関係と情報フローを定義
- 条件付きエッジで動的ルーティング
"""

from strands import Agent
from strands.multiagent.graph import GraphBuilder

# =============================================================================
# 専門エージェントの定義
# =============================================================================

classifier = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはカスタマーサポートの問い合わせ分類エージェントです。
問い合わせを分析し、以下のいずれかのカテゴリに分類してください。
必ず「カテゴリ: 」の後にカテゴリ名のみを書いてください。

カテゴリ: technical
カテゴリ: billing
カテゴリ: product""",
    name="classifier"
)

technical_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは技術サポートの専門エージェントです。
技術的な問題に対して具体的なトラブルシューティング手順を提供してください。""",
    name="technical"
)

billing_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは請求・支払いの専門エージェントです。
請求に関する問い合わせに対して正確で丁寧な案内を提供してください。""",
    name="billing"
)

product_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは商品レコメンデーションの専門エージェントです。
ユーザーの要件と予算に合わせた具体的な商品提案を行ってください。""",
    name="product"
)

qa_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは品質保証エージェントです。
他のエージェントが生成した回答を最終チェックし、問題があれば修正してください。
問題がなければ「【最終回答】」の後に回答を記載してください。""",
    name="qa"
)

# =============================================================================
# Graph の構築と実行
# =============================================================================

def run_graph_pattern():
    """Graph パターンでカスタマーサポートを実行"""

    print("=" * 60)
    print(" Graph パターン: 条件分岐型カスタマーサポート")
    print("=" * 60)

    # テスト用の問い合わせ
    queries = [
        "APIキーを再生成したいのですが、管理画面のどこから操作できますか？",
        "今月のサブスクリプション料金がいつもより高いです。内訳を教えてください。",
        "チームで使えるプロジェクト管理ツールを探しています。10人規模です。",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'─' * 60}")
        print(f"  問い合わせ {i}: {query}")
        print(f"{'─' * 60}")

        # ノード 1: 分類
        print("\n  [Node: Classifier] 問い合わせを分類中...")
        classification_result = classifier(
            f"以下の問い合わせを分類してください：\n{query}"
        )
        classification_text = str(classification_result)
        print(f"  → {classification_text[:200]}")

        # 条件分岐（エッジ）: 分類結果に基づいてルーティング
        print("\n  [Edge: Routing] 分類結果に基づいてルーティング...")

        if "technical" in classification_text.lower():
            print("  → 技術サポートエージェントにルーティング")
            specialist_response = technical_agent(
                f"以下の技術的な問い合わせに対応してください：\n{query}"
            )
        elif "billing" in classification_text.lower():
            print("  → 請求エージェントにルーティング")
            specialist_response = billing_agent(
                f"以下の請求に関する問い合わせに対応してください：\n{query}"
            )
        else:
            print("  → 商品レコメンデーションエージェントにルーティング")
            specialist_response = product_agent(
                f"以下の商品に関する問い合わせに対応してください：\n{query}"
            )

        print(f"  → 専門エージェント回答: {str(specialist_response)[:300]}...")

        # ノード: QA チェック
        print("\n  [Node: QA] 品質保証チェック中...")
        final_response = qa_agent(
            f"以下の回答を品質チェックしてください：\n"
            f"元の問い合わせ: {query}\n"
            f"エージェント回答: {specialist_response}"
        )
        print(f"  → 最終回答:\n{final_response}")

    print("\n" + "=" * 60)
    print(" Graph パターン完了")
    print("=" * 60)
    print("\n[考察ポイント]")
    print("- 分類結果に基づいて動的にルーティングが行われる")
    print("- 各専門エージェントは独立して処理を行う（分離性）")
    print("- QA エージェントが最終品質を保証する（品質ゲート）")
    print("- ノードの追加・変更が容易（拡張性）")


if __name__ == "__main__":
    run_graph_pattern()
