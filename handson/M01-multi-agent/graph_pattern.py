"""
モジュール 1: Graph パターン - 条件分岐を含むカスタマーサポート

Strands Agents SDK の Graph パターンを使用して、
条件分岐を含む構造化されたフローチャート型のオーケストレーションを実装します。

Graph の特徴:
- ノードはエージェント、カスタムノード、またはマルチエージェントシステムを表す
- エッジはノード間の依存関係と情報フローを定義
- 実行は依存関係を遵守し、グラフ構造に従う
- 周期的なパターンで見直すことができる
"""

import json
from strands import Agent
from strands.multiagent.graph import Graph, GraphNode, GraphEdge


# =============================================================================
# 専門エージェントの定義
# =============================================================================

# 分類ノード
classifier = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはカスタマーサポートの問い合わせ分類エージェントです。
問い合わせを分析し、必ず以下の形式で分類結果を返してください：

カテゴリ: [technical / billing / product]
信頼度: [高 / 中 / 低]
要約: [問い合わせの要約]
ルーティング先: [technical_agent / billing_agent / product_agent]"""
)

# 技術サポートエージェント
technical_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは技術サポートの専門エージェントです。
以下の領域に精通しています：
- ログイン・認証の問題
- アプリケーションエラー
- パフォーマンスの問題
- API 接続の問題

具体的なトラブルシューティング手順を提供してください。
解決できない場合は、エスカレーションが必要である旨を明記してください。"""
)

# 請求エージェント
billing_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは請求・支払いの専門エージェントです。
以下の領域に精通しています：
- 料金の内訳説明
- 返金処理の案内
- プラン変更の手続き
- 支払い方法の更新

正確な金額や期限を含む具体的な案内を提供してください。"""
)

# 商品レコメンデーションエージェント
product_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは商品レコメンデーションの専門エージェントです。
以下の領域に精通しています：
- ユーザーの要件に基づく商品提案
- 商品比較と特徴説明
- 在庫状況の確認
- 関連商品の提案

ユーザーの予算や要件に合わせた具体的な提案を行ってください。"""
)

# 品質保証エージェント（最終チェック）
qa_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは品質保証エージェントです。
他のエージェントが生成した回答を最終チェックし、以下を確認してください：

1. 回答が問い合わせに対して適切か
2. 情報に誤りや矛盾がないか
3. トーンが丁寧でプロフェッショナルか
4. 具体的なアクションアイテムが含まれているか

問題がある場合は修正案を提示し、問題がなければ承認してください。

最終回答を「【最終回答】」の後に記載してください。"""
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
                f"以下の技術的な問い合わせに対応してください：\n"
                f"問い合わせ: {query}\n"
                f"分類情報: {classification_text}"
            )
        elif "billing" in classification_text.lower():
            print("  → 請求エージェントにルーティング")
            specialist_response = billing_agent(
                f"以下の請求に関する問い合わせに対応してください：\n"
                f"問い合わせ: {query}\n"
                f"分類情報: {classification_text}"
            )
        else:
            print("  → 商品レコメンデーションエージェントにルーティング")
            specialist_response = product_agent(
                f"以下の商品に関する問い合わせに対応してください：\n"
                f"問い合わせ: {query}\n"
                f"分類情報: {classification_text}"
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
