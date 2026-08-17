"""
モジュール 2: 会話マネージャー比較デモ

SlidingWindowConversationManager と SummarizingConversationManager の
動作を比較し、長い会話でのコンテキスト管理の違いを確認します。

1. SlidingWindow: 古いメッセージを単純に切り捨て（情報が失われる）
2. Summarizing: 要約して圧縮（重要情報を保持）

※ SummarizingConversationManager の要約は ContextWindowOverflowError 発生時に
  リアクティブに実行されます。Nova Pro (300K tokens) では 20 ターン程度の会話では
  溢れないため、このデモでは SlidingWindow の動作を見せた上で、Summarizing との
  違いを説明します。本番環境での動作については steps.md パート3 を参照。
"""

from strands import Agent
from strands.agent.conversation_manager import (
    SlidingWindowConversationManager,
    SummarizingConversationManager,
)

# =============================================================================
# パート 1: SlidingWindowConversationManager（切り捨て動作のデモ）
# =============================================================================

def demo_sliding_window():
    """SlidingWindow で古いメッセージが切り捨てられる様子を確認"""

    print("=" * 70)
    print(" パート1: SlidingWindowConversationManager（メッセージ切り捨て）")
    print("=" * 70)
    print("""
  設定:
    window_size: 4（最大 4 ペアのメッセージを保持）

  → 5ターン目以降、古いメッセージが消える = 情報が完全に失われる
    """)

    # window_size=4: 最大 4 つの user/assistant ペアを保持
    sliding_manager = SlidingWindowConversationManager(window_size=4)

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt="""あなたは EC サイトのカスタマーサポートエージェントです。
顧客の問い合わせに丁寧に対応し、問題解決を支援します。
過去の会話の文脈を理解した上で回答してください。""",
        conversation_manager=sliding_manager,
    )

    # 会話シナリオ: 重要な情報を最初に伝え、後半で参照する
    conversation_turns = [
        "こんにちは。注文番号 ORD-2026-78901 について問い合わせたいです。",
        "届いた液晶モニターが破損していました。画面右下にひびがあります。",
        "配送業者はヤマト運輸で、購入日は8月10日です。",
        "支払いはクレジットカードで、交換を希望します。",
        "あと、サブスクリプション SUB-456789 の料金も確認してください。",
        "月額2,980円のはずが4,980円になっています。",
        # ここで初期の情報が切り捨てられているはず
        "先ほどの注文番号は何でしたっけ？最初にお伝えした情報をまとめてください。",
    ]

    print(f"  会話ターン数: {len(conversation_turns)}")
    print(f"{'─' * 70}")

    for i, user_message in enumerate(conversation_turns, 1):
        print(f"\n  [ターン {i}] ユーザー: {user_message}")

        response = agent(user_message)
        response_text = str(response)

        msg_count = len(agent.messages)
        print(f"  エージェント: {response_text[:200]}...")
        print(f"  [メッセージ数: {msg_count}]", end="")

        if msg_count < i * 2:
            print(f" ← 切り捨て発生！（期待: {i*2}, 実際: {msg_count}）")
        else:
            print()

    print(f"\n{'─' * 70}")
    print(f"  [結果] 最終メッセージ数: {len(agent.messages)}（window_size=4 → 最大8メッセージ）")
    print(f"  → 注文番号 ORD-2026-78901 の情報は切り捨てられ、回答できない可能性が高い")


# =============================================================================
# パート 2: SummarizingConversationManager（要約による保持）
# =============================================================================

def demo_summarizing():
    """SummarizingConversationManager の設定と本番での動作を説明"""

    print(f"\n\n{'=' * 70}")
    print(" パート2: SummarizingConversationManager（要約で情報保持）")
    print("=" * 70)
    print("""
  SummarizingConversationManager は SlidingWindow と異なり、
  古いメッセージを単純に削除するのではなく「要約」して保持します。

  ┌──────────────────────────────────────────────────────────────────┐
  │ 動作の違い                                                        │
  ├──────────────────────────────────────────────────────────────────┤
  │                                                                    │
  │  SlidingWindow:                                                    │
  │    [msg1][msg2][msg3][msg4][msg5][msg6] → [msg5][msg6]            │
  │     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                   │
  │     完全に削除（情報喪失）                                         │
  │                                                                    │
  │  Summarizing:                                                      │
  │    [msg1][msg2][msg3][msg4][msg5][msg6]                            │
  │     → [要約: msg1-4の重要情報][msg5][msg6]                        │
  │        ^^^^^^^^^^^^^^^^^^^^^^^^                                    │
  │        注文番号、顧客名、決定事項を保持                            │
  │                                                                    │
  └──────────────────────────────────────────────────────────────────┘

  要約のトリガー条件:
    - ContextWindowOverflowError が発生した時（リアクティブ）
    - モデルのコンテキストウィンドウが実際に飽和した時に初めて発動
    - Nova Pro (300K tokens) の場合、数百ターンの会話で発動
    """)

    # 同じ会話を SummarizingConversationManager で実行
    summarizing_manager = SummarizingConversationManager(
        summary_ratio=0.5,
        preserve_recent_messages=4,
    )

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt="""あなたは EC サイトのカスタマーサポートエージェントです。
顧客の問い合わせに丁寧に対応し、問題解決を支援します。
過去の会話の文脈を理解した上で回答してください。""",
        conversation_manager=summarizing_manager,
    )

    # 同じシナリオ
    conversation_turns = [
        "こんにちは。注文番号 ORD-2026-78901 について問い合わせたいです。",
        "届いた液晶モニターが破損していました。画面右下にひびがあります。",
        "配送業者はヤマト運輸で、購入日は8月10日です。",
        "支払いはクレジットカードで、交換を希望します。",
        "あと、サブスクリプション SUB-456789 の料金も確認してください。",
        "月額2,980円のはずが4,980円になっています。",
        "先ほどの注文番号は何でしたっけ？最初にお伝えした情報をまとめてください。",
    ]

    print(f"  会話ターン数: {len(conversation_turns)}")
    print(f"{'─' * 70}")

    for i, user_message in enumerate(conversation_turns, 1):
        print(f"\n  [ターン {i}] ユーザー: {user_message}")

        response = agent(user_message)
        response_text = str(response)

        msg_count = len(agent.messages)
        print(f"  エージェント: {response_text[:200]}...")
        print(f"  [メッセージ数: {msg_count}]")

    print(f"\n{'─' * 70}")
    print(f"  [結果] 最終メッセージ数: {len(agent.messages)}")
    print(f"  → コンテキストウィンドウに余裕があるため全メッセージ保持")
    print(f"  → 注文番号 ORD-2026-78901 の情報を正しく回答できる")
    print(f"""
  [比較まとめ]
  ┌───────────────────┬─────────────────────┬──────────────────────────┐
  │                   │ SlidingWindow       │ Summarizing              │
  ├───────────────────┼─────────────────────┼──────────────────────────┤
  │ 7ターン目の回答   │ ❌ 情報喪失の可能性  │ ✅ 全情報を保持          │
  │ メッセージ数      │ 8（固定上限）        │ {len(agent.messages)}（全保持 or 要約）     │
  │ 情報の扱い        │ 古いものを削除       │ 要約して圧縮保持         │
  │ 適用場面          │ 短い会話/簡易用途    │ 本番環境推奨             │
  └───────────────────┴─────────────────────┴──────────────────────────┘
    """)


# =============================================================================
# 3種類のマネージャーの比較（参考情報）
# =============================================================================

def compare_managers():
    """3種類の会話マネージャーの特徴を比較"""

    print(f"{'─' * 70}")
    print("  [参考] 3種類の会話マネージャー")
    print(f"{'─' * 70}")
    print("""
    ┌─────────────────────────────────────────────────────────────────┐
    │ マネージャー              │ 動作              │ 用途            │
    ├─────────────────────────────────────────────────────────────────┤
    │ NullConversationManager  │ 何もしない         │ デバッグ/短会話  │
    │ SlidingWindow...         │ 古いメッセージ削除  │ 簡易的な制限    │
    │ Summarizing...           │ 要約して圧縮       │ 本番環境推奨    │
    └─────────────────────────────────────────────────────────────────┘

    SummarizingConversationManager のメリット:
    1. 重要な情報（名前、注文番号、決定事項）を要約に保持
    2. ツール呼び出しのペアを壊さない
    3. 直近メッセージは完全に保持（文脈の連続性）
    4. 要約が失敗した場合のフォールバックあり

    ※ パラメータ詳細・本番推奨設定は steps.md パート3 を参照
    """)


if __name__ == "__main__":
    demo_sliding_window()
    demo_summarizing()
    compare_managers()
