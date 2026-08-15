# モジュール 1: マルチエージェントアーキテクチャと通信パターン - ハンズオン手順

## パート 1: Bedrock Playground でマルチエージェントの必要性を体感する（10分）

### ステップ 1.1: Bedrock チャットプレイグラウンドを開く

1. AWS コンソールで **Amazon Bedrock** を開く: https://console.aws.amazon.com/bedrock/
2. 左ナビゲーションペインの **Test playgrounds** → **Chat/Text** を選択
3. **Select model** をクリック
4. **Amazon** → **Nova Pro** を選択し **Apply** をクリック

### ステップ 1.2: シングルエージェントの限界を体感する

以下のプロンプトを入力して、1 つのモデルに複数ドメインの複雑なタスクを依頼します：

```
あなたは以下の3つの役割を同時に担当するカスタマーサポートエージェントです：
1. 技術サポート（ログインエラー、API問題）
2. 請求サポート（料金、返金処理）
3. 商品レコメンデーション（予算と要件に基づく提案）

以下の問い合わせに対応してください：
「APIキーのエラーが出ていて困っています。あと先月の請求が高かった理由も知りたいです。それと予算5万円でチーム向けのプロジェクト管理ツールを探しています。」
```

**観察ポイント**：
- 3 つの異なるドメインを 1 つの回答で処理しようとする
- 各領域の深い専門性が発揮されにくい
- コンテキストが長くなると品質が低下する可能性

→ これがマルチエージェントアーキテクチャが必要な理由です

---

## パート 2: Workflow パターン（10分）

### ステップ 2.1: プロジェクトの準備

```bash
cd ~/handson/M01-multi-agent
```

### ステップ 2.2: Workflow パターンの確認と実行

`workflow_pattern.py` はカスタマーサポートのワークフローを以下の順序で実行します：
1. **分類エージェント** → 2. **調査エージェント** → 3. **回答エージェント**

```bash
python workflow_pattern.py
```

出力を確認し、以下を議論します：
- 各エージェントが順次実行される流れ
- 前のエージェントの出力が次の入力になる
- 予測可能だが柔軟性は低い

### ステップ 2.3: 結果の考察

- **利点**: 予測可能な動作、デバッグしやすい、包括的なステート管理
- **制限**: 柔軟性が低い、すべてのパスを事前に定義する必要がある
- **適したユースケース**: ドキュメント処理パイプライン、データ ETL、承認ワークフロー

---

## パート 3: Graph パターン（10分）

### ステップ 3.1: Graph パターンの実行

```bash
python graph_pattern.py
```

Graph パターンの構造：
```
                    ┌──────────────┐
                    │   Classifier  │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │Technical │ │ Billing  │ │  Product │
        │  Agent   │ │  Agent   │ │  Agent   │
        └──────┬───┘ └──────┬───┘ └──────┬───┘
              └────────────┼────────────┘
                           ▼
                    ┌──────────────┐
                    │  QA Agent    │
                    └──────────────┘
```

### ステップ 3.2: 結果の考察

- **利点**: 条件分岐が可能、構造化されつつも柔軟
- **制限**: Graph の設計が複雑になる可能性
- **適したユースケース**: カスタマーサポートルーティング、コンテンツ審査

---

## パート 4: Swarm パターン（10分）

### ステップ 4.1: Swarm パターンの実行

```bash
python swarm_pattern.py
```

Swarm パターンの特徴：
- 各エージェントが別のエージェントに引き継ぐタイミングを自律的に決定
- すべてのエージェントが共有コンテキストにアクセス可能
- 創発的知能の原理に基づく動作

### ステップ 4.2: 結果の考察

- **利点**: 高い柔軟性、自律的な問題解決、多様な視点の統合
- **制限**: 予測が困難、デバッグが難しい
- **適したユースケース**: 創造的な問題解決、複雑な意思決定

---

## パート 5: AgentCore Memory の作成と共有メモリ（コンソール + CLI）（15分）

### ステップ 5.1: AgentCore Memory の作成（コンソール）

1. **Amazon Bedrock AgentCore** コンソールを開く
2. 左ナビゲーションペインで **Memory** を選択
3. **Create memory** をクリック
4. 以下を入力：
   - **Memory name**: `customer_support_shared_memory`
   - **Short-term memory (raw event) expiration**: `7` days
5. **Additional configurations** を展開：
   - **Memory description**: `Shared memory for multi-agent customer support`

6. **Long-term memory extraction strategies** セクションで組み込み戦略を追加：

   **セマンティックメモリ戦略の追加:**
   1. **組み込み戦略** セクションの **Add strategy** ボタンをクリック
   2. ドロップダウンから **セマンティックメモリ** を選択
   3. 設定ダイアログが表示される：
      - **戦略名前**: 自動生成された名前のまま（例: `semantic_builtin_xxxxx`）
      - **名前空間**: デフォルトのまま（`/strategies/{memoryStrategyId}/actors/{actorId}/`）
      - **Metadata definition**: デフォルトのまま
   4. **Create strategy** をクリック

   **要約戦略の追加:**
   1. 再度 **Add strategy** ボタンをクリック
   2. ドロップダウンから **要約** を選択
   3. 設定ダイアログが表示される：
      - **戦略名前**: 自動生成された名前のまま（例: `summary_builtin_xxxxx`）
      - **名前空間**: デフォルトのまま（`/strategies/{memoryStrategyId}/actors/{actorId}/sessions/{sessionId}/`）
      - **Metadata definition**: デフォルトのまま
   4. **Create strategy** をクリック

   > ℹ️ 他にも「ユーザープリファレンス」「Episodes」が選択可能です。今回は上記 2 つで十分です。

7. **Create memory** をクリック

### ステップ 5.2: 作成した Memory の確認

作成された Memory の詳細ページで以下を確認：
- **Memory ID**: （このIDをメモ。複数エージェントで共有するため）
- **Status**: `ACTIVE`
- **Strategies**: 設定した抽出戦略

### ステップ 5.3: 共有メモリデモの実行

```bash
python shared_memory_demo.py
```

出力を確認し、以下を議論します：
- 各エージェントが個別の `actor_id` を持ちつつ同じ `memory_id` を共有
- セマンティック検索による関連メモリの取得
- エージェント間でのコンテキストの引き継ぎ

### ステップ 5.4: AgentCore Memory の共有パラメータ

| パラメータ | 共有/個別 | 説明 |
|-----------|----------|------|
| `memory_id` | **共有** | 同じメモリリソースへのアクセス |
| `session_id` | **共有** | 同じセッション内での状態共有 |
| `actor_id` | **個別** | 各エージェントのアイデンティティ |

---

## パート 6: MCP ツールとしてのエージェント（5分）

### ステップ 6.1: MCP 統合デモの実行

```bash
python mcp_tool_agent.py
```

ツールとしてのエージェントパターンの特徴：
- プライマリオーケストレーターがツールとしてエージェントを呼び出す
- 疎結合で再利用性が高い
- AgentCore Gateway で本番環境の認証・発見を一元管理

---

## パート 7: パターン比較とディスカッション（5分）

### パターン比較表

| 観点 | Workflow | Graph | Swarm | MCP (ツール) |
|------|----------|-------|-------|-------------|
| 制御性 | 高い | 高い | 低い | 中程度 |
| 柔軟性 | 低い | 中程度 | 高い | 中程度 |
| デバッグ容易性 | 容易 | 中程度 | 困難 | 容易 |
| 再利用性 | 低い | 中程度 | 低い | 高い |
| 適用場面 | 定型処理 | 条件分岐処理 | 創造的タスク | プラットフォーム横断 |

### ディスカッションポイント

1. **パターン選択の基準**: どのような要件でどのパターンを選ぶべきか
2. **セキュリティの影響**: 各パターンでのセキュリティ上の懸念事項の違い
3. **本番環境への適用**: シンプルに開始して反復する重要性
4. **コストとレイテンシー**: パターンごとのトレードオフ

### 実装に関する推奨事項

- 包括的なログ記録とモニタリングを実装する
- 障害に備えたエラーハンドリングを設計する
- シンプルに開始して反復する
- 明確なエージェントのロールを定義する
- コストとレイテンシーを追跡する
- オブザーバビリティを最初から実装する

---

## 参考ドキュメント

- [Amazon Bedrock AgentCore Memory - メモリの作成](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-create-a-memory-store.html)
- [Amazon Bedrock AgentCore - マルチエージェントコラボレーション](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agents-multi-agent.html)
- [Strands Agents SDK - Multi-Agent Orchestration](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/)
- [Strands Agents SDK - Swarm パターン](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/)
- [Strands Agents SDK - Graph パターン](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/)
- [Amazon Bedrock Playgrounds](https://docs.aws.amazon.com/bedrock/latest/userguide/playgrounds.html)
- [Model Context Protocol (MCP) 概要](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-mcp.html)
- [AgentCore Gateway](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway.html)
