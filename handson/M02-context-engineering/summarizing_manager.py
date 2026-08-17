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

    print("\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  パート1: SlidingWindowConversationManager                          ║")
    print("║  （トリミング = 古いメッセージの選択的削除）                         ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │ 設定: window_size = 4（最大 4 ペアのメッセージを保持）         │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │ スライド対応:                                                   │")
    print("  │   「トリミングまたはプルーニング - 選択的トークン削除」          │")
    print("  │   → 古い順にメッセージを削除するため、重要情報も失われる       │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    sliding_manager = SlidingWindowConversationManager(window_size=4)

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=sliding_manager,
    )

    print(f"  会話ターン数: {len(CONVERSATION_TURNS)}")
    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for i, user_message in enumerate(CONVERSATION_TURNS, 1):
        print()
        print(f"  ┌─ ターン {i:2d} ─────────────────────────────────────────────────────")
        print(f"  │ ユーザー: {user_message}")
        response = agent(user_message)
        response_text = str(response)
        print(f"  │ エージェント: {response_text[:120]}...")
        msg_count = len(agent.messages)
        if msg_count < i * 2:
            print(f"  │")
            print(f"  │ 📊 メッセージ数: {msg_count}  ⚠️  切り捨て発生（古いメッセージを削除）")
        else:
            print(f"  │")
            print(f"  │ 📊 メッセージ数: {msg_count}")
        print(f"  └──────────────────────────────────────────────────────────────────")

    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print("  ┌─ 結果 ───────────────────────────────────────────────────────────")
    print(f"  │ 最終メッセージ数: {len(agent.messages)}（window_size=4 → 最大 8 メッセージ）")
    print(f"  │ 削除されたメッセージ: {len(CONVERSATION_TURNS) * 2 - len(agent.messages)}")
    print(f"  │")
    print(f"  │ ❌ 注文番号 ORD-2026-78901 や配送情報は完全に失われた")
    print(f"  │ ❌ 最後の「まとめてください」に正確に回答できない可能性が高い")
    print(f"  └──────────────────────────────────────────────────────────────────")


# =============================================================================
# パート 2: Summarizing — 要約（軌跡の凝縮）
# =============================================================================

def demo_summarizing():
    """SummarizingConversationManager で要約による圧縮を実演"""

    print("\n\n")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  パート2: SummarizingConversationManager                            ║")
    print("║  （要約 = 軌跡の凝縮で重要情報を保持）                              ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  ┌────────────────────────────────────────────────────────────────┐")
    print("  │ 設定:                                                          │")
    print("  │   summary_ratio: 0.5（50% のメッセージを要約）                 │")
    print("  │   preserve_recent_messages: 4（直近 4 メッセージを保持）        │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │ スライド対応: 「要約 - 軌跡の凝縮」                             │")
    print("  │   → 意味を保持しながら情報を凝縮                               │")
    print("  │   → 構造化された箇条書き形式の要約で重要情報を取得             │")
    print("  │   → ツール使用と結果のペアを分断しない                         │")
    print("  ├────────────────────────────────────────────────────────────────┤")
    print("  │ ※ 本来は ContextWindowOverflow 時に自動発動                    │")
    print("  │   デモでは毎ターン reduce_context() を呼び出して動作確認       │")
    print("  └────────────────────────────────────────────────────────────────┘")
    print()

    summarizing_manager = SummarizingConversationManager(
        summary_ratio=0.5,              # 50% を要約
        preserve_recent_messages=4,     # 直近4メッセージを保持
    )

    agent = Agent(
        model="us.amazon.nova-pro-v1:0",
        system_prompt=SYSTEM_PROMPT,
        conversation_manager=summarizing_manager,
    )

    print(f"  会話ターン数: {len(CONVERSATION_TURNS)}")
    print(f"  毎ターン reduce_context() を呼び出し → 要約の発生を観察")
    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for i, user_message in enumerate(CONVERSATION_TURNS, 1):
        print()
        print(f"  ┌─ ターン {i:2d} ─────────────────────────────────────────────────────")
        print(f"  │ ユーザー: {user_message}")

        response = agent(user_message)
        response_text = str(response)
        print(f"  │ エージェント: {response_text[:120]}...")

        msg_count_before = len(agent.messages)
        print(f"  │")
        print(f"  │ 📊 メッセージ数: {msg_count_before}")

        # reduce_context を毎ターン呼び出し
        try:
            summarizing_manager.reduce_context(agent)
            msg_count_after = len(agent.messages)
            if msg_count_after < msg_count_before:
                print(f"  │")
                print(f"  │ ⚡ 要約発生!")
                print(f"  │    メッセージ: {msg_count_before} → {msg_count_after}"
                      f"（{msg_count_before - msg_count_after} 件を圧縮）")
                print(f"  │")
                # 要約メッセージの内容を表示
                first_msg = agent.messages[0]
                content = first_msg.get("content", [])
                if content and isinstance(content, list):
                    text = content[0].get("text", "")
                    lines = text.split("\n")
                    print(f"  │ ┌─ 要約内容 ──────────────────────────────────────────")
                    for line in lines[:10]:
                        if line.strip():
                            print(f"  │ │ {line}")
                    if len(lines) > 10:
                        print(f"  │ │ ... (以下省略)")
                    print(f"  │ └─────────────────────────────────────────────────────")
        except Exception:
            pass

        print(f"  └──────────────────────────────────────────────────────────────────")

    # 最終状態
    print()
    print("  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"  ┌─ 最終状態 ──────────────────────────────────────────────────────")
    print(f"  │ 最終メッセージ数: {len(agent.messages)}")
    print(f"  │ → 要約により古いメッセージが圧縮されつつ、重要情報は保持")
    print(f"  └──────────────────────────────────────────────────────────────────")

    # 要約後に追加質問して情報保持を確認
    print()
    print("  ┌─ 情報保持の確認 ─────────────────────────────────────────────────")
    test_question = "最初に伝えた注文番号と、報告した2つの問題を教えてください。"
    print(f"  │ 質問: {test_question}")
    response = agent(test_question)
    print(f"  │")
    response_lines = str(response)[:400].split("\n")
    for line in response_lines:
        print(f"  │ {line}")
    print(f"  └──────────────────────────────────────────────────────────────────")

    print()
    print()
    print("  ╔════════════════════════════════════════════════════════════════════╗")
    print("  ║  SlidingWindow vs Summarizing 比較                                ║")
    print("  ╠════════════════════════════════════════════════════════════════════╣")
    print("  ║                   │ SlidingWindow        │ Summarizing            ║")
    print("  ╟───────────────────┼──────────────────────┼────────────────────────╢")
    print("  ║ 削減方法          │ 古いメッセージを削除 │ 要約して圧縮           ║")
    print("  ║ 情報保持          │ ❌ 失われる          │ ✅ 要約に保持          ║")
    print("  ║ コンテキスト品質  │ 低い                 │ 高い                   ║")
    print("  ║ 追加コスト        │ なし                 │ 要約生成のLLM呼び出し  ║")
    print("  ║ 適用場面          │ 簡易用途             │ 本番環境推奨           ║")
    print("  ╚════════════════════════════════════════════════════════════════════╝")
    print()


# =============================================================================
# パラメータ解説
# =============================================================================

def show_parameters():
    """SummarizingConversationManager のパラメータを解説"""

    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  [参考] SummarizingConversationManager のパラメータ                  ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print()
    print("  ┌────────────────────────────────┬───────────┬──────────────────────┐")
    print("  │ パラメータ                     │ デフォルト│ 説明                 │")
    print("  ├────────────────────────────────┼───────────┼──────────────────────┤")
    print("  │ summary_ratio                  │ 0.3       │ 要約する割合(0.1~0.8)│")
    print("  │ preserve_recent_messages       │ 10        │ 常に保持するメッセージ│")
    print("  │ summarization_agent            │ None      │ 要約用カスタムAgent   │")
    print("  │ summarization_system_prompt    │ None      │ 要約用プロンプト      │")
    print("  └────────────────────────────────┴───────────┴──────────────────────┘")
    print()
    print("  ┌─────────────────────────────────┬──────────────────┬──────────────┐")
    print("  │ マネージャー                    │ 動作             │ 用途         │")
    print("  ├─────────────────────────────────┼──────────────────┼──────────────┤")
    print("  │ NullConversationManager         │ 変更なし         │ デバッグ     │")
    print("  │ SlidingWindowConversation...    │ 固定ウィンドウ   │ 簡易的な制限 │")
    print("  │ SummarizingConversation...      │ インテリジェント要約│ 本番推奨  │")
    print("  └─────────────────────────────────┴──────────────────┴──────────────┘")
    print()
    print("  ※ 詳細は steps.md パート3 を参照")
    print()


if __name__ == "__main__":
    demo_sliding_window()
    demo_summarizing()
    show_parameters()
