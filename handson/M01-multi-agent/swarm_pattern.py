"""
モジュール 1: Swarm パターン - 自律的エージェントコラボレーション

Strands Agents SDK の Swarm パターンを使用して、
エージェントが自律的にハンドオフする動的コラボレーションを実装します。

Swarm の特徴:
- 創発的知能の原理に基づいて動作
- 各エージェントが別のエージェントに引き継ぐタイミングを決定できる
- すべてのエージェントが共有コンテキストにアクセス可能
"""

from strands import Agent
from strands.multiagent.swarm import Swarm


# =============================================================================
# 専門エージェントの定義（Swarm 用）
# =============================================================================

research_analyst = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはリサーチアナリストです。必ず日本語で回答してください。
与えられた問題に対して、データ収集と分析を行います。

あなたの役割：
- 問題の背景と現状を調査する
- 関連するデータポイントを収集する
- 定量的な分析結果を提供する

分析結果を構造化して報告してください。""",
    name="research_analyst"
)

strategy_consultant = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは戦略コンサルタントです。必ず日本語で回答してください。
リサーチ結果に基づいて、戦略的な提案を行います。

あなたの役割：
- ビジネスインパクトを評価する
- 複数の選択肢を提示し、推奨案を示す
- リスクと機会を特定する

戦略提案をエグゼクティブサマリー形式で報告してください。""",
    name="strategy_consultant"
)

implementation_engineer = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは実装エンジニアです。必ず日本語で回答してください。
戦略的な提案を具体的な実装計画に落とし込みます。

あなたの役割：
- 技術的な実現可能性を評価する
- 具体的な実装ステップを定義する
- タイムラインとリソース要件を見積もる

実装計画をフェーズ別に報告してください。""",
    name="implementation_engineer"
)


# =============================================================================
# Swarm の構築と実行
# =============================================================================

def run_swarm_pattern():
    """Swarm パターンで複雑な問題解決を実行"""

    print("=" * 60)
    print(" Swarm パターン: 自律的エージェントコラボレーション")
    print("=" * 60)

    # Swarm の構成
    swarm = Swarm(
        nodes=[research_analyst, strategy_consultant, implementation_engineer],
    )

    # テストシナリオ
    scenarios = [
        {
            "title": "EC サイトの AI チャットボット導入",
            "query": (
                "当社の EC サイト（月間アクティブユーザー 50 万人）に "
                "AI チャットボットを導入したい。現在のカスタマーサポートは "
                "電話とメールのみで、平均応答時間は 24 時間。"
                "予算は年間 3000 万円。最適な導入戦略を提案してください。"
            )
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─' * 60}")
        print(f"  シナリオ {i}: {scenario['title']}")
        print(f"{'─' * 60}")
        print(f"  問題: {scenario['query'][:80]}...")

        print("\n  [Swarm 実行開始] エージェントが自律的にコラボレーション...")
        print("  (各エージェントが自分で引き継ぎタイミングを判断します)")
        print()

        result = swarm(scenario["query"])

        print(f"\n  [Swarm 結果]")
        print(f"  {result}")

    print("\n" + "=" * 60)
    print(" Swarm パターン完了")
    print("=" * 60)
    print("\n[考察ポイント]")
    print("- エージェントが自律的にハンドオフのタイミングを判断した")
    print("- 各エージェントが全コンテキスト（タスク・履歴・共有知識）にアクセスできた")
    print("- 最終的に複数の視点を統合した包括的な回答が生成された")
    print("- 実行パスは事前に予測できない（創発的知能）")


if __name__ == "__main__":
    run_swarm_pattern()
