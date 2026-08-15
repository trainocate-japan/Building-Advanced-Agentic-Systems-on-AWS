"""
モジュール 1: Swarm パターン - 自律的エージェントコラボレーション

Strands Agents SDK の Swarm パターンを使用して、
エージェントが自律的にハンドオフする動的コラボレーションを実装します。

Swarm の特徴:
- 創発的知能の原理に基づいて動作
- 各エージェントが別のエージェントに引き継ぐタイミングを決定できる
- すべてのエージェントが共有コンテキストにアクセス可能
- オリジナルのタスク、履歴、共有知識にアクセスできる
"""

from strands import Agent, tool
from strands.multiagent.swarm import Swarm


# =============================================================================
# 専門エージェントの定義（Swarm 用）
# =============================================================================

# リサーチアナリストエージェント
research_analyst = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたはリサーチアナリストです。
与えられた問題に対して、データ収集と分析を行います。

あなたの役割：
- 問題の背景と現状を調査する
- 関連するデータポイントを収集する
- 定量的な分析結果を提供する

他のエージェントに引き継ぐべき場合：
- 戦略的な意思決定が必要な場合 → strategy_consultant に引き継ぐ
- 実装の詳細が必要な場合 → implementation_engineer に引き継ぐ

分析結果を構造化して報告してください。""",
    name="research_analyst"
)

# 戦略コンサルタントエージェント
strategy_consultant = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは戦略コンサルタントです。
リサーチ結果に基づいて、戦略的な提案を行います。

あなたの役割：
- ビジネスインパクトを評価する
- 複数の選択肢を提示し、推奨案を示す
- リスクと機会を特定する

他のエージェントに引き継ぐべき場合：
- 追加のデータ分析が必要な場合 → research_analyst に引き継ぐ
- 技術的な実現可能性の確認が必要な場合 → implementation_engineer に引き継ぐ

戦略提案をエグゼクティブサマリー形式で報告してください。""",
    name="strategy_consultant"
)

# 実装エンジニアエージェント
implementation_engineer = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは実装エンジニアです。
戦略的な提案を具体的な実装計画に落とし込みます。

あなたの役割：
- 技術的な実現可能性を評価する
- 具体的な実装ステップを定義する
- タイムラインとリソース要件を見積もる

他のエージェントに引き継ぐべき場合：
- コスト分析が必要な場合 → research_analyst に引き継ぐ
- ビジネス上の判断が必要な場合 → strategy_consultant に引き継ぐ

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
        agents=[research_analyst, strategy_consultant, implementation_engineer],
        swarm_name="business_advisory_swarm"
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
        {
            "title": "マルチエージェントシステムのスケーリング",
            "query": (
                "現在 3 つのエージェントで運用しているカスタマーサポートシステムを "
                "10 エージェントに拡張したい。現在の課題はレイテンシーの増大と "
                "エージェント間の状態同期の問題。AWS 上での最適なアーキテクチャと "
                "スケーリング戦略を提案してください。"
            )
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'─' * 60}")
        print(f"  シナリオ {i}: {scenario['title']}")
        print(f"{'─' * 60}")
        print(f"  問題: {scenario['query'][:100]}...")

        # Swarm を実行
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
    print("\n[Workflow/Graph との比較]")
    print("- Workflow: 事前定義された順序 → 予測可能だが柔軟性が低い")
    print("- Graph: 条件分岐 → 構造化されつつ柔軟")
    print("- Swarm: 自律的判断 → 最も柔軟だが予測が困難")


if __name__ == "__main__":
    run_swarm_pattern()
