# モジュール 2: コンテキストエンジニアリングとパフォーマンスの最適化 - ハンズオン手順

## パート 1: 入力形式の最適化（10分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M02-context-engineering
```

### ステップ 1.2: トークン使用量の比較

`context_optimization.py` を確認します。同じ情報を異なる形式（Pretty JSON vs TOON）で表現した場合のトークン使用量の差を比較します。

TOON（Token-Oriented Object Notation）の特徴：
- JSON の冗長な構造（括弧、引用符、インデント）を排除
- 意味を保ちながらトークン数を 30%+ 削減
- LLM が十分に解析可能な形式

### ステップ 1.3: 最適化デモの実行

```bash
python context_optimization.py
```

出力を確認し、以下を議論します：
- Pretty JSON と TOON のトークン数の差
- 同一クエリに対する回答品質の比較
- コスト削減の見積もり（月間 100 万リクエストで ~30% 削減）

---

## パート 2: プロンプトキャッシュ（コンソール + CLI）（15分）

### ステップ 2.1: Bedrock Playground でプロンプトキャッシュを体感する（コンソール）

Bedrock チャットプレイグラウンドでプロンプトキャッシュの効果を直接確認します。

1. AWS コンソールで **Amazon Bedrock** を開く: https://console.aws.amazon.com/bedrock/
2. 左ナビゲーションペインの **Test playgrounds** → **Chat/Text** を選択
3. **Select model** をクリック
4. **Anthropic** → **Claude Sonnet 4.6** を選択し、推論プロファイルで **US Claude Sonnet 4.6** を選択して **適用**

### ステップ 2.2: プロンプトキャッシュの有効化

1. 左側の設定パネルを下にスクロール
2. **Guardrails** セクションの下にある **プロンプトキャッシュ** のトグルを **ON** にする

> ℹ️ サポートされているモデル（Claude Sonnet/Haiku 等）では、デフォルトで有効になっている場合もあります。

### ステップ 2.3: キャッシュの動作確認

1. 以下の長いシステムプロンプトを **System prompt** に入力：

```
あなたはエンタープライズ向けカスタマーサポートの専門エージェントです。

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
```

2. **User message** に入力して **Run**：
```
パスワードをリセットしたいです
```

3. 回答が生成されたら、右上のトークン情報を確認：
   - **入力**: 入力トークン数
   - **出力**: 出力トークン数
   - **レイテンシー**: 応答時間（ミリ秒）

5. 続けて別の質問を入力して **実行**：
```
今月の請求額が高い理由を教えてください
```

6. 再度右上のトークン情報を確認：
   - 入力トークン数が初回と同程度であれば、キャッシュが効いてレイテンシーが短縮されているはずです

### ステップ 2.4: キャッシュチェックポイントの確認

1. 左側パネル下部の「**キャッシュチェックポイントを表示する**」リンクをクリック
2. ダイアログが表示され、キャッシュの仕様を確認：
   - プロンプトとモデル応答の合計サイズが **1,024 トークン**を超えるとチェックポイント作成が開始
   - その後 **1,024 トークンごと**に新しいチェックポイントが生成（最大 4 個）
   - 会話をアイドル状態で **5 分間**放置するとキャッシュは期限切れになる
3. ダイアログ内にキャッシュされたコンテンツのプレビューが表示されることを確認
4. **閉じる** をクリック

### ステップ 2.5: プロンプトキャッシュのコスト効果（説明）

```
┌─────────────────────────────────────────────────────┐
│ プロンプトキャッシュのコスト構造                       │
├─────────────────────────────────────────────────────┤
│                                                       │
│  初回: キャッシュ書き込み = 通常料金の 1.25倍         │
│  2回目以降: キャッシュ読み取り = 通常料金の 0.1倍     │
│                                                       │
│  → 同じプロンプトを 2回以上使えばコスト削減効果あり  │
│  → 10回使えば 90% のコスト削減                       │
│                                                       │
│  最適な配置順序（キャッシュ効率最大化）:              │
│  1. システムプロンプト（静的）  ← キャッシュ         │
│  2. ツール定義（静的）          ← キャッシュ         │
│  3. 参照ドキュメント（準静的）  ← キャッシュ         │
│  4. 会話履歴（動的）                                  │
│  5. ユーザー入力（動的）                              │
└─────────────────────────────────────────────────────┘
```

### ステップ 2.6: Prompt Management でテンプレート管理（コンソール）

プロンプトをバージョン管理し、チームで共有する方法を確認します。

1. Bedrock コンソールの左メニューから **Prompt management** を選択
2. **Create prompt** をクリック
3. 以下を入力：
   - **Name**: `customer-support-system-prompt`
   - **Description**: `カスタマーサポートエージェント用システムプロンプト`
4. **Create prompt** をクリック
5. **Prompt builder** が開く：
   - **Generative AI resource** で **Claude Sonnet 4** を選択
   - **System prompt** にステップ 2.3 のシステムプロンプトを入力
   - **User message** に `{{customer_query}}` と入力（変数テンプレート）
6. **Test variables** セクションで `customer_query` に `請求について質問があります` と入力
7. **Run** をクリックしてテスト

このように Prompt Management を使うことで：
- プロンプトのバージョン管理が可能
- チーム間でのプロンプト共有
- A/B テストによる品質改善

---

## パート 3: コンテキスト圧縮 - SummarizingConversationManager（10分）

### ステップ 3.1: 会話管理の課題

長い会話ではコンテキストウィンドウが飽和し、以下の問題が発生：
- 初期の重要な情報が「忘れられる」
- 応答品質が低下する
- 処理時間とコストが増大する

Strands SDK の 3 種類の会話マネージャー：

| マネージャー | 動作 | 用途 |
|-------------|------|------|
| NullConversationManager | 何もしない | デバッグ/短い会話 |
| SlidingWindowConversationManager | 古いメッセージ削除 | 簡易的な制限 |
| **SummarizingConversationManager** | **要約して圧縮** | **本番環境推奨** |

### ステップ 3.2: SlidingWindow vs Summarizing の比較デモ

```bash
python summarizing_manager.py
```

このデモは 3 フェーズで構成されています:

**パート 1: SlidingWindowConversationManager（トリミング/プルーニング）**
- `window_size=4` に設定し、最大 4 ペアのメッセージのみ保持
- 5 ターン目以降、古いメッセージが完全に削除される
- 最後のターンで「注文番号は何でしたっけ？」と聞くと、情報が失われているため回答できない
- スライド対応: 「トリミングまたはプルーニング - 選択的トークン削除」

**パート 2: SummarizingConversationManager（要約 = 軌跡の凝縮）**
- 同じ会話を蓄積した後、`reduce_context()` を呼び出して要約を実行
- 古いメッセージが「構造化された箇条書き形式の要約」に圧縮される
- 要約後に質問しても、注文番号や問題の詳細を正しく回答できる
- スライド対応: 「要約 - 軌跡の凝縮」「インテリジェントな要約」

> ⚠️ **デモでの `reduce_context()` 手動呼び出しについて**
>
> 本番環境では `reduce_context()` は ContextWindowOverflowError 発生時に
> 自動的に呼び出されます。Nova Pro (300K tokens) のコンテキストウィンドウは
> 非常に大きいため、10 ターン程度では溢れません。
> デモでは要約の動作を確認するために手動で呼び出しています。

確認ポイント:
- 要約メッセージの内容（注文番号、問題の詳細が構造化されて保持されている）
- メッセージ数の削減（例: 20 → 6）
- 要約後も情報が正しく回答される

### ステップ 3.3: パラメータチューニング

| パラメータ | デフォルト | 説明 |
|-----------|----------|------|
| `summary_ratio` | 0.3 | コンテキスト削減時に要約する割合（0.1〜0.8） |
| `preserve_recent_messages` | 10 | 常に保持する最近のメッセージ数 |
| `summarization_agent` | None | 要約用のカスタムエージェント |
| `summarization_system_prompt` | None | 要約用のカスタムシステムプロンプト |

**要約の発動条件（本番環境）:**

| 条件 | 動作 |
|------|------|
| コンテキストウィンドウに余裕あり | 何もしない（全メッセージ保持） |
| ContextWindowOverflowError 発生 | `summary_ratio` 分のメッセージを要約に圧縮 |

**SlidingWindow との使い分け:**

| 状況 | 推奨マネージャー |
|------|-----------------|
| 短い会話（〜10ターン） | NullConversationManager |
| コスト重視・情報喪失許容 | SlidingWindowConversationManager |
| 本番環境・長い会話 | **SummarizingConversationManager** |

**本番環境での推奨設定:**

```python
from strands.agent.conversation_manager import SummarizingConversationManager

conversation_manager = SummarizingConversationManager(
    summary_ratio=0.3,              # 30% を要約
    preserve_recent_messages=10,    # 直近10件を保持
)
```

---

## パート 4: コンテキスト分離 - マルチエージェント境界（5分）

### ステップ 4.1: コンテキスト分離デモの実行

```bash
python context_isolation.py
```

### ステップ 4.2: 比較結果の確認

出力されるテーブルを確認：

| 観点 | 一括処理（アンチパターン） | コンテキスト分離（推奨） |
|------|--------------------------|------------------------|
| コンテキストサイズ | 大（全情報を1エージェントに） | 小（必要最小限） |
| ディストラクション | 高い | 低い |
| 回答品質 | 中（情報過多） | 高（集中） |
| 並列実行 | 不可 | 可能 |
| コスト | 高い | 効率的 |

委任の指針：
- 簡単な事実確認: 1 エージェント、3〜10 回のツール呼び出し
- 複雑な研究: 10+ エージェント、役割を明確に分離

---

## パート 5: ディスカッション（5分）

### コンテキスト最適化戦略の選択基準

| 状況 | 推奨戦略 |
|------|---------|
| トークンコストが高い | 入力形式の最適化（TOON） |
| 同じプロンプトを繰り返し使用 | プロンプトキャッシュ |
| 長時間の会話 | SummarizingConversationManager |
| セッション間の情報保持 | AgentCore Memory（外部書き込み） |
| 複数ドメインの問い合わせ | コンテキスト分離（マルチエージェント） |

### コンテキストの障害モード

| 障害モード | 説明 | 対策 |
|-----------|------|------|
| ポイズニング | 不完全な情報から誤った前提を構築 | 入力バリデーション |
| ディストラクション | コンテキストが多すぎて集中できない | コンテキスト分離 |
| 混同 | 無関係な情報で不適切なツール呼び出し | 専門エージェント化 |
| クラッシュ | 矛盾した指示で意思決定が停止 | 優先度付け |

---

## 参考ドキュメント

- [Amazon Bedrock - プロンプトキャッシュ](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html)
- [Amazon Bedrock - Prompt Management](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management.html)
- [Amazon Bedrock - プロンプトの作成 (Prompt Management)](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-management-create.html)
- [Amazon Bedrock AgentCore Memory - メモリの概要](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory.html)
- [Amazon Bedrock AgentCore Memory - RetrieveMemoryRecords](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-retrieve.html)
- [Strands Agents SDK - Conversation Management](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/conversation-management/)
- [Amazon Bedrock - Converse API リファレンス](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
