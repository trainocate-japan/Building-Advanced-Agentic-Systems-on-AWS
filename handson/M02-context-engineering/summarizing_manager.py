"""
モジュール 2: SummarizingConversationManager - インテリジェントな会話要約

Strands SDK の SummarizingConversationManager を使用して、
長い会話でコンテキストウィンドウが飽和する問題を自動的に解決します。

動作:
- トークン制限を超えると自動的にコンテキストを削減
- 構造化された要約で重要情報を保持
- ツール使用と結果のペアを分断しない
- 直近のメッセージは常に保持

※ デモ用に proactive_compression の閾値を低く設定しています。
  本番設定については steps.md を参照してください。
"""

from strands import Agent
from strands.agent.conversation_manager import SummarizingConversationManager

# =============================================================================
# SummarizingConversationManager の設定
# =============================================================================

# 要約マネージャーの設定（デモ用 - 閾値を低くして要約発動を確認しやすくしている）
# 本番設定については steps.md パート3 を参照
conversation_manager = SummarizingConversationManager(
    summary_ratio=0.5,              # 50% のメッセージを要約（デモ用に積極的に）
    preserve_recent_messages=4,     # 直近 4 メッセージを保持（デモ用に少なく）
    proactive_compression={"compression_threshold": 0.05},  # 5% で要約発動（デモ用）
)

# エージェントの作成
agent = Agent(
    model="us.amazon.nova-pro-v1:0",
    system_prompt="""あなたは EC サイトのカスタマーサポートエージェントです。
顧客の問い合わせに丁寧に対応し、問題解決を支援します。
過去の会話の文脈を理解した上で回答してください。""",
    conversation_manager=conversation_manager,
)


# =============================================================================
# 長い会話のシミュレーション
# =============================================================================

def simulate_long_conversation():
    """20回以上のやり取りをシミュレートして要約の動作を確認"""

    print("=" * 70)
    print(" SummarizingConversationManager: 長い会話の自動要約")
    print("=" * 70)
    print(f"""
  設定（デモ用 - 要約発動を確認しやすい設定）:
    summary_ratio: 0.5（50% を要約）
    preserve_recent_messages: 4（直近4件を保持）
    proactive_compression: 5%（コンテキスト使用率 5% で要約発動）

  ※ 本番環境での推奨設定は steps.md パート3 を参照

  シナリオ: 顧客が複数の問題を段階的に報告する長い会話
    """)

    # 長い会話をシミュレート
    conversation_turns = [
        # 初期の問い合わせ
        "こんにちは。注文番号 ORD-2026-78901 について問い合わせたいのですが。",
        "この注文、3日前に届いたんですが、商品が破損していました。",
        "液晶モニターなんですが、画面の右下に大きなひびが入っています。",
        "開封時に撮影した写真があります。交換か返金をお願いしたいです。",
        # 追加情報
        "配送業者はヤマト運輸でした。梱包は問題なさそうでした。",
        "購入日は8月10日で、到着が8月12日です。",
        "支払いはクレジットカードです。",
        # 別の問題の追加
        "あと、もう一つ聞きたいことがあるんですが...",
        "先月のサブスクリプション更新で、プランが変わっていたみたいなんです。",
        "月額2,980円のプランだったのに、4,980円のプランに変更されています。",
        "変更した覚えはないのですが、確認していただけますか？",
        # さらに詳細
        "サブスクリプションID は SUB-456789 です。",
        "先月のメールを確認しましたが、プラン変更の通知は来ていません。",
        "2つの問題を整理すると、破損モニターの交換と、サブスク料金の訂正です。",
        # フォローアップ
        "モニターの交換品はいつ届きますか？",
        "交換品が届くまでの間、一時的に代替品を借りることはできますか？",
        "サブスクリプションの方は、差額を返金してもらえますか？",
        "あと、今後こういった誤変更が起きないように対策はありますか？",
        # 最終確認
        "ありがとうございます。最後に確認させてください。",
        "対応いただく内容を箇条書きでまとめていただけますか？",
    ]

    print(f"  会話ターン数: {len(conversation_turns)}")
    print(f"\n{'─' * 70}")

    for i, user_message in enumerate(conversation_turns, 1):
        print(f"\n  [ターン {i}/{len(conversation_turns)}] ユーザー: {user_message[:60]}...")

        # エージェントに送信
        response = agent(user_message)

        # 応答を表示（短縮）
        response_text = str(response)
        print(f"  エージェント: {response_text[:150]}...")

        # コンテキストサイズの追跡（メッセージ数で代用）
        msg_count = len(agent.messages)
        print(f"  [コンテキスト] メッセージ数: {msg_count}")

        # 要約が発生したかチェック
        if msg_count < i * 2:  # 通常は user+assistant で2つずつ増える
            print(f"  ⚡ 要約が発生した可能性あり（メッセージ数が期待値より少ない）")

    # 最終状態の確認
    print(f"\n{'─' * 70}")
    print(f"  [最終状態]")
    print(f"  会話ターン数: {len(conversation_turns)}")
    print(f"  最終メッセージ数: {len(agent.messages)}")
    print(f"  要約により削減されたメッセージ: {len(conversation_turns) * 2 - len(agent.messages)}")

    # コンテキスト内容の確認
    print(f"\n  [コンテキスト内の要約メッセージ]")
    for msg in agent.messages[:3]:  # 最初の数メッセージを確認
        if msg.get("role") == "assistant":
            content = msg.get("content", [{}])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                if "要約" in text or "Summary" in text.lower():
                    print(f"  要約: {text[:200]}...")
                    break


# =============================================================================
# 3種類のマネージャーの比較
# =============================================================================

def compare_managers():
    """3種類の会話マネージャーの特徴を比較"""

    print(f"\n{'─' * 70}")
    print("  [参考] 3種類の会話マネージャー比較")
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
    simulate_long_conversation()
    compare_managers()
