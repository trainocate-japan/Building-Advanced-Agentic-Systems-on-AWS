"""
モジュール 2: 会話マネージャー比較デモ

SlidingWindowConversationManager と SummarizingConversationManager の
動作の違いを実演し、コンテキスト圧縮戦略を理解します。

スライド対応:
- コンテキスト圧縮戦略（要約 vs トリミング/プルーニング）
- 3種類の会話マネージャー
- SummarizingConversationManager の概要とパラメータ
"""

from strands import Agent
from strands.agent.conversation_manager import (
    SlidingWindowConversationManager,
    SummarizingConversationManager,
)

# =============================================================================
# 共通: 会話シナリオ
# =============================================================================

# 顧客が複数の重要情報を段階的に伝えるシナリオ
CONVERSATION_TURNS = [
    "こんにちは。注文番号 ORD-2026-78901 について問い合わせたいです。",
    "届いた液晶モニターが破損していました。画面右下にひびがあります。",
    "配送業者はヤマト運輸で、購入日は8月10日、到着は8月12日です。",
    "支払いはクレジットカードで、交換を希望します。",
    "あと、サブスクリプション SUB-456789 の料金も確認してください。",
    "月額2,980円のはずが4,980円になっています。変更した覚えはありません。",
    "2つの問題を整理すると、破損モニターの交換と、サブスク料金の訂正です。",
    "モニターの交換品はいつ届きますか？",
    "サブスクリプションの差額は返金してもらえますか？",
    "最後に、対応内容をまとめてください。最初に伝えた注文番号も含めて。",
]

SYSTEM_PROMPT = """あなたは EC サイトのカスタマーサポートエージェントです。
顧客の問い合わせに丁寧に対応し、問題解決を支援します。
過去の会話の文脈を理解した上で回答してください。"""


# =============================================================================
# パート 1: SlidingWindow — トリミング/プルーニング（選択的トークン削除）
# =============================================================================

def demo_sliding_window():
    """SlidingWindow で古いメッセージが切り捨てられる様子を確認"""

    print("=" * 70)
    print(" パート1: SlidingWindowConversationManager")
    print("        （トリミング = 古いメッセージの選択的削除）")
    print("=" * 70)
    print("""
  設定: window_size=4（最大 4 ペアのメッセージを保持）

  スライド対応: 「トリミングまたはプルーニング - 選択的トークン削除」
  → 重要な情報に寄与しないトークンを戦略的に削除
  → 実際には「古い順に削除」なので重要情報も失われる
    """)

    sliding_manager = SlidingWindowConversationManager(window_size=4)

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=sliding_manager,
    )

    print(f"  会話ターン数: {len(CONVERSATION_TURNS)}")
    print(f"{'─' * 70}")

    for i, user_message in enumerate(CONVERSATION_TURNS, 1):
        print(f"\n  [ターン {i:2d}] ユーザー: {user_message[:50]}...")
        response = agent(user_message)
        response_text = str(response)
        msg_count = len(agent.messages)
        print(f"           エージェント: {response_text[:100]}...")
        print(f"           [メッセージ数: {msg_count}]", end="")
        if msg_count < i * 2:
            print(f" ← 切り捨て発生（古いメッセージを削除）")
        else:
            print()

    print(f"\n{'─' * 70}")
    print(f"  [結果]")
    print(f"  最終メッセージ数: {len(agent.messages)}（window_size=4 → 最大8メッセージ）")
    print(f"  削除されたメッセージ: {len(CONVERSATION_TURNS) * 2 - len(agent.messages)}")
    print(f"  → 注文番号 ORD-2026-78901 や配送情報は完全に失われた")
    print(f"  → 最後の「まとめてください」に正確に回答できない可能性が高い")


# =============================================================================
# パート 2: Summarizing — 要約（軌跡の凝縮）
# =============================================================================

def demo_summarizing():
    """SummarizingConversationManager で要約による圧縮を実演"""

    print(f"\n\n{'=' * 70}")
    print(" パート2: SummarizingConversationManager")
    print("        （要約 = 軌跡の凝縮で重要情報を保持）")
    print("=" * 70)
    print("""
  設定:
    summary_ratio: 0.5（50%% のメッセージを要約）
    preserve_recent_messages: 4（直近4メッセージを保持）

  スライド対応: 「要約 - 軌跡の凝縮」
  → 意味を保持しながら情報を凝縮
  → 構造化された箇条書き形式の要約で重要情報を取得
  → ツール使用と結果のペアを分断しない

  ※ 本来は ContextWindowOverflow 時に自動発動しますが、
    デモのため会話蓄積後に手動で reduce_context を呼び出して
    要約の動作を確認します。
    """)

    summarizing_manager = SummarizingConversationManager(
        summary_ratio=0.5,              # 50% を要約
        preserve_recent_messages=4,     # 直近4メッセージを保持
    )

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=summarizing_manager,
    )

    # まず会話を蓄積
    print(f"  [フェーズ1] 会話を蓄積中...")
    print(f"{'─' * 70}")

    for i, user_message in enumerate(CONVERSATION_TURNS, 1):
        print(f"  [ターン {i:2d}] ユーザー: {user_message[:50]}...")
        response = agent(user_message)
        response_text = str(response)
        print(f"           エージェント: {response_text[:100]}...")

    msg_count_before = len(agent.messages)
    print(f"\n{'─' * 70}")
    print(f"  [フェーズ1 完了] メッセージ数: {msg_count_before}")

    # reduce_context を手動で呼び出して要約を実行
    print(f"\n  [フェーズ2] reduce_context() を呼び出して要約を実行...")
    print(f"{'─' * 70}")

    summarizing_manager.reduce_context(agent)

    msg_count_after = len(agent.messages)
    print(f"  要約前メッセージ数: {msg_count_before}")
    print(f"  要約後メッセージ数: {msg_count_after}")
    print(f"  削減されたメッセージ: {msg_count_before - msg_count_after}")

    # 要約メッセージの内容を確認
    print(f"\n  [要約メッセージの内容]")
    print(f"{'─' * 70}")
    for msg in agent.messages:
        if msg.get("role") == "user":
            content = msg.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                if len(text) > 200 and ("summary" in text.lower() or "要約" in text
                                        or "conversation" in text.lower()):
                    print(f"  [要約発見] role=user (要約は user メッセージとして挿入)")
                    print(f"  {text[:500]}")
                    print(f"  ..." if len(text) > 500 else "")
                    break
        elif msg.get("role") == "assistant":
            content = msg.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                if len(text) > 200 and ("summary" in text.lower() or "要約" in text
                                        or "conversation" in text.lower()
                                        or "ORD-2026" in text):
                    print(f"  [要約発見] role=assistant")
                    print(f"  {text[:500]}")
                    print(f"  ..." if len(text) > 500 else "")
                    break
    else:
        # 要約メッセージが見つからない場合、最初のメッセージを表示
        if agent.messages:
            first_msg = agent.messages[0]
            content = first_msg.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                print(f"  [最初のメッセージ] role={first_msg.get('role')}")
                print(f"  {text[:500]}")

    # 要約後に追加質問して、情報が保持されているか確認
    print(f"\n\n  [フェーズ3] 要約後に情報保持を確認")
    print(f"{'─' * 70}")
    test_question = "最初に伝えた注文番号と、報告した2つの問題を教えてください。"
    print(f"  質問: {test_question}")
    response = agent(test_question)
    print(f"  回答: {str(response)[:300]}")

    print(f"\n{'─' * 70}")
    print(f"""
  [結果]
  → 要約により {msg_count_before - msg_count_after} メッセージが 1 つの要約に圧縮された
  → 注文番号 ORD-2026-78901、破損モニター、サブスク料金の情報が保持されている
  → SlidingWindow と異なり、重要情報が失われない

  [SlidingWindow との比較]
  ┌───────────────────┬──────────────────────┬──────────────────────────┐
  │                   │ SlidingWindow        │ Summarizing              │
  ├───────────────────┼──────────────────────┼──────────────────────────┤
  │ 削減方法          │ 古いメッセージを削除  │ 要約して圧縮             │
  │ 情報保持          │ ❌ 失われる           │ ✅ 要約に保持            │
  │ コンテキスト品質  │ 低い                  │ 高い                     │
  │ 追加コスト        │ なし                  │ 要約生成のLLM呼び出し    │
  │ 適用場面          │ 簡易用途              │ 本番環境推奨             │
  └───────────────────┴──────────────────────┴──────────────────────────┘
    """)


# =============================================================================
# パラメータ解説
# =============================================================================

def show_parameters():
    """SummarizingConversationManager のパラメータを解説"""

    print(f"{'=' * 70}")
    print(" [参考] SummarizingConversationManager のパラメータ")
    print(f"{'=' * 70}")
    print("""
    ┌────────────────────────────────┬───────────┬──────────────────────────┐
    │ パラメータ                      │ デフォルト │ 説明                     │
    ├────────────────────────────────┼───────────┼──────────────────────────┤
    │ summary_ratio                  │ 0.3       │ 要約する割合 (0.1〜0.8)  │
    │ preserve_recent_messages       │ 10        │ 常に保持するメッセージ数  │
    │ summarization_agent            │ None      │ 要約用カスタムエージェント│
    │ summarization_system_prompt    │ None      │ 要約用カスタムプロンプト  │
    └────────────────────────────────┴───────────┴──────────────────────────┘

    3種類の会話マネージャー:
    ┌─────────────────────────────────┬───────────────────┬────────────────┐
    │ マネージャー                     │ 動作               │ 用途           │
    ├─────────────────────────────────┼───────────────────┼────────────────┤
    │ NullConversationManager         │ 変更なし            │ デバッグ/短会話│
    │ SlidingWindowConversationManager│ 固定ウィンドウ維持  │ 簡易的な制限   │
    │ SummarizingConversationManager  │ インテリジェントな要約│ 本番環境推奨  │
    └─────────────────────────────────┴───────────────────┴────────────────┘

    ※ 詳細は steps.md パート3 を参照
    """)


if __name__ == "__main__":
    demo_sliding_window()
    demo_summarizing()
    show_parameters()
