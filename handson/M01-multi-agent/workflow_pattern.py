"""
モジュール 1: Workflow パターン - マルチエージェントカスタマーサポート

Strands Agents SDK を使用して、事前定義された順序で
専門エージェントが連携するパイプラインを構築します。

Workflow パターンの特徴:
- 各ステップは決定論的に順次実行される
- 前のエージェントの出力が次のエージェントの入力になる
- 堅牢なエラー処理とステート管理が可能

※ Strands SDK では Graph を直線的に構成することで Workflow を実現します。
"""

from strands import Agent
from strands.multiagent.graph import Graph, GraphBuilder

# =============================================================================
# 専門エージェントの定義
# =============================================================================

# 分類エージェント: 問い合わせ内容を分類する
classifier_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはカスタマーサポートの問い合わせ分類エージェントです。
ユーザーの問い合わせを以下のカテゴリに分類してください：

- technical: 技術的な問題（ログインできない、エラーが発生する等）
- billing: 請求・支払いに関する問題（料金の不明点、返金要求等）
- product: 商品に関する問い合わせ（レコメンデーション、在庫確認等）

必ず以下の形式で回答してください:
カテゴリ: [カテゴリ名]
要約: [問い合わせの要約]""",
    name="classifier"
)

# 調査エージェント: 関連情報を収集する
research_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはカスタマーサポートの調査エージェントです。
分類結果に基づいて、問題解決に必要な情報を収集・整理してください。

以下の情報を提供してください：
- 関連するFAQ項目
- 推奨される解決策
- エスカレーションが必要かどうか""",
    name="researcher"
)

# 回答生成エージェント: 最終回答を生成する
response_agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはカスタマーサポートの回答生成エージェントです。
分類結果と調査結果に基づいて、顧客に送信する最終回答を生成してください。

回答は以下の要件を満たす必要があります：
- 丁寧で専門的なトーン
- 具体的な解決策や次のステップを含む
- 必要に応じてエスカレーション先を案内""",
    name="responder"
)

# =============================================================================
# Workflow（順次パイプライン）の実行
# =============================================================================

def run_workflow():
    """Workflow パターンでカスタマーサポートを実行"""

    print("=" * 60)
    print(" Workflow パターン: カスタマーサポートパイプライン")
    print("=" * 60)

    # テスト用の問い合わせ
    queries = [
        "先月の請求額が通常の2倍になっているのですが、明細を確認していただけますか？",
        "アプリにログインしようとするとエラーコード E-403 が表示されます。",
        "新しいノートパソコンを探しています。予算15万円でおすすめはありますか？",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n{'─' * 60}")
        print(f"  問い合わせ {i}: {query}")
        print(f"{'─' * 60}")

        # Step 1: 分類
        print("\n  [Step 1] 分類エージェント...")
        classification = classifier_agent(
            f"以下の問い合わせを分類してください：\n{query}"
        )
        print(f"  → 分類結果: {classification}")

        # Step 2: 調査
        print("\n  [Step 2] 調査エージェント...")
        research = research_agent(
            f"以下の分類結果に基づいて調査してください：\n"
            f"問い合わせ: {query}\n"
            f"分類: {classification}"
        )
        print(f"  → 調査結果: {research}")

        # Step 3: 回答生成
        print("\n  [Step 3] 回答生成エージェント...")
        response = response_agent(
            f"以下の情報に基づいて最終回答を生成してください：\n"
            f"問い合わせ: {query}\n"
            f"分類: {classification}\n"
            f"調査結果: {research}"
        )
        print(f"  → 最終回答:\n{response}")

    print("\n" + "=" * 60)
    print(" Workflow 完了")
    print("=" * 60)
    print("\n[考察ポイント]")
    print("- 各ステップが順次実行され、前のステップの出力が次の入力になる")
    print("- エラーが発生した場合、どのステップで失敗したか特定しやすい")
    print("- 処理順序が事前に決まっているため、予測可能な動作を保証できる")


if __name__ == "__main__":
    run_workflow()
