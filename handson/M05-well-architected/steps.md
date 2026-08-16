# モジュール 5: Well-Architected エージェンティック AI システム - ハンズオン手順

## パート 1: Well-Architected Tool で Agentic AI Lens レビューを実行する（15分）

### ステップ 1.1: Well-Architected Tool コンソールを開く

1. AWS コンソールで **AWS Well-Architected Tool** を開く: https://console.aws.amazon.com/wellarchitected/
2. 左ナビゲーションペインで **Workloads** を選択

### ステップ 1.2: ワークロードを作成する

1. **Define workload** をクリック
2. 以下を入力：
   - **Workload name**: `Agentic Customer Support System`
   - **Description**: `Multi-agent customer support system built with Strands SDK and AgentCore`
   - **Environment**: `Pre-production`
   - **Regions**: `US East (N. Virginia)`
   - **Account IDs**: 自分のアカウント ID
3. **Next** をクリック
4. **Apply profiles** はスキップして **Next** をクリック

### ステップ 1.3: Agentic AI Lens を適用する

1. **Apply lenses** ページで **Lens Catalog** タブを選択
2. 検索ボックスに `Agentic` と入力
3. **Agentic AI Lens** にチェックを入れる
4. **Define Workload** をクリック

### ステップ 1.4: Agentic AI Lens のレビューを開始する

1. 作成されたワークロードの概要ページが表示される
2. **Lenses** セクションで **Agentic AI Lens** の **Start reviewing** をクリック
3. レビュー画面が表示される

### ステップ 1.5: レビュー質問に回答する

Agentic AI Lens の質問に、本ハンズオンで学んだ内容を基に回答します。以下はピラーごとの主な質問例です：

**セキュリティ（M03 の内容）:**
- エージェントのアイデンティティと認証をどのように管理していますか？
  → AgentCore Identity (OAuth 2LO/3LO)、IAM ロール
- エージェントの行動をどのように制御していますか？
  → AgentCore Policy (Cedar)、Bedrock Guardrails
- 監査証跡をどのように実装していますか？
  → CloudTrail、CloudWatch Logs の監査ログ

**信頼性（M01 の内容）:**
- エージェント間の通信障害にどのように対処していますか？
  → サーキットブレーカー、フォールバック、グレースフルデグラデーション
- マルチエージェントのオーケストレーションパターンは？
  → Graph パターンで条件分岐、Swarm で自律的ハンドオフ

**パフォーマンス効率（M02 の内容）:**
- コンテキストウィンドウをどのように管理していますか？
  → SummarizingConversationManager、プロンプトキャッシュ、TOON 形式
- メモリと状態をどのように管理していますか？
  → AgentCore Memory（セマンティック + 要約戦略）

**運用上の優秀性（M04 の内容）:**
- エージェントのオブザーバビリティをどのように実装していますか？
  → ADOT SDK + AgentCore Observability、CloudWatch ダッシュボード
- エージェントの品質をどのように評価していますか？
  → AgentCore Evaluations（LLM-as-a-Judge）、カスタムエバリュエーター

いくつかの質問に回答して、リスク評価がどのように変わるか確認してください。

### ステップ 1.6: リスク評価を確認する

1. 回答後、ワークロード概要ページに戻る
2. **Agentic AI Lens** のリスクサマリーを確認：
   - **High risk**: 未対応のベストプラクティス
   - **Medium risk**: 部分的に対応
   - **No risk**: 対応済み
3. **Improvement plan** をクリックして改善提案を確認

---

#### 運用上の優秀性

```
□ OpenTelemetry でエージェント実行をトレースしているか（M04）
□ CloudWatch ダッシュボードで主要メトリクスを可視化しているか（M04）
□ アラームで異常を早期検出できるか（M04）
□ 評価パイプラインで品質を継続的に測定しているか（M04）
□ 段階的デプロイ戦略があるか（カナリア/ブルーグリーン）
□ ロールバック手順が定義されているか
```

#### セキュリティ

```
□ AgentCore Identity で認証を設定しているか（M03）
□ AgentCore Policy (Cedar) でアクション制御をしているか（M03）
□ Guardrails で PII 保護・コンテンツフィルターを設定しているか（M03）
□ 監査ログですべてのアクションを記録しているか（M03）
□ 最小権限の原則を適用しているか
□ ネットワーク分離（VPC/PrivateLink）を検討しているか
```

#### 信頼性

```
□ サーキットブレーカーでカスケード障害を防いでいるか
□ フォールバック先モデル/エージェントが定義されているか
□ グレースフルデグラデーションが実装されているか
□ リトライ戦略（指数バックオフ）が設定されているか
□ 障害時の回復パターンが定義されているか
□ 冗長性（バックアップインスタンス）があるか
```

#### パフォーマンス効率

```
□ コンテキスト最適化（TOON、圧縮）を適用しているか（M02）
□ プロンプトキャッシュを活用しているか（M02）
□ SummarizingConversationManager で長い会話に対応しているか（M02）
□ 適切なモデルを選択しているか（複雑度に応じた動的選択）
□ コンテキスト分離でパフォーマンスを最適化しているか（M02）
□ 並列実行で全体レイテンシーを削減しているか
```

#### コスト最適化

```
□ トークン使用量を追跡しているか
□ 動的モデル選択（複雑度に応じた安価モデルの活用）を行っているか
□ キャッシュでトークンコストを削減しているか
□ 不要な推論を排除しているか
□ バッチ処理可能なタスクをまとめているか
□ コスト異常検知アラームを設定しているか
```

#### サステナビリティ

```
□ 効率的なプロンプト設計でトークン消費を最小化しているか
□ 軽量モデル（Nova Lite）を適切に活用しているか
□ 不要なエージェント呼び出しを排除しているか
□ キャッシュとメモリで重複計算を回避しているか
```

---

## パート 2: 設計アクティビティ（20分）

### ステップ 2.1: シナリオの説明

以下のシナリオに基づいてアーキテクチャを設計します：

**マルチエージェント e コマースカスタマーサポートシステム**

要件：
- 月間 100 万件の問い合わせを処理
- 3 種類の専門エージェント（技術、請求、商品）
- 平均応答時間 5 秒以内
- 24/7 稼働、99.9% 可用性
- PCI-DSS 準拠（カード情報保護）
- コスト上限: 月額 $50,000

### ステップ 2.2: グループディスカッション

以下の 4 つの観点でアーキテクチャを設計・議論します：

#### 観点 1: 通信パターンとオーケストレーション

- どの通信パターンを選択するか？（Workflow / Graph / Swarm / MCP）
- コンテキスト最適化戦略は？
- メモリ共有の方式は？

**推奨回答例**:
```
- Graph パターン: 分類→専門エージェント→QA の構造化フロー
- コンテキスト分離: 各専門エージェントは自ドメインのみ
- AgentCore Memory: session_id を共有、actor_id で分離
- プロンプトキャッシュ: 共通システムプロンプトをキャッシュ
```

#### 観点 2: 本番環境のアーキテクチャとデプロイ

- AgentCore Runtime でのデプロイ方式は？
- スケーリング戦略は？
- デプロイパイプラインは？

**推奨回答例**:
```
- AgentCore Runtime: コンテナベースデプロイ
- Auto Scaling: リクエスト数に基づく自動スケール
- Blue/Green デプロイ: 新バージョンの段階的リリース
- Feature Flag: 新エージェントの A/B テスト
```

#### 観点 3: セキュリティ設計

- 認証・認可の方式は？
- データ保護の方法は？
- 監査要件への対応は？

**推奨回答例**:
```
- AgentCore Identity: OAuth 2.0 (3LO) でユーザー認証
- AgentCore Policy: Cedar で返金上限・営業時間制限
- Guardrails: PII マスキング + コンテンツフィルター
- CloudTrail: すべてのアクションを監査記録
- VPC + PrivateLink: ネットワーク分離
```

#### 観点 4: オブザーバビリティと評価

- モニタリングの構成は？
- 品質評価の方法は？
- インシデント対応の流れは？

**推奨回答例**:
```
- OpenTelemetry: トレース・スパンレベルの計測
- CloudWatch: ダッシュボード + P95 レイテンシーアラーム
- AgentCore Evaluations: Helpfulness + Faithfulness 定期評価
- カスタムエバリュエーター: PCI-DSS 準拠チェック
- PagerDuty 連携: エラー率 5% 超過で即時通知
```

---

## パート 3: 本番準備状況のレビュー（10分）

### ステップ 3.1: デプロイ準備チェックリスト

| カテゴリ | チェック項目 | 状態 |
|---------|------------|------|
| パフォーマンス | 負荷テスト完了 | □ |
| パフォーマンス | ベースラインメトリクス確立 | □ |
| パフォーマンス | P95 レイテンシー < 5秒確認 | □ |
| セキュリティ | ポリシーテスト完了 | □ |
| セキュリティ | IAM レビュー完了 | □ |
| セキュリティ | 脆弱性スキャン完了 | □ |
| モニタリング | CloudWatch ダッシュボード構築 | □ |
| モニタリング | アラーム設定完了 | □ |
| モニタリング | トレーシング有効化 | □ |
| モニタリング | 評価パイプライン稼働 | □ |
| コンプライアンス | PCI-DSS 要件確認 | □ |
| コンプライアンス | データレジデンシー確認 | □ |
| コンプライアンス | 監査ログ設定確認 | □ |
| 運用 | ロールバック手順確認 | □ |
| 運用 | インシデント対応手順確認 | □ |
| 運用 | オンコール体制確認 | □ |

### ステップ 3.2: 既存システムとの統合ベストプラクティス

```
1. 最初からオブザーバビリティを考慮して設計する
2. Well-Architected の原則をすべての統合レイヤーに適用する
3. エージェントとツール間の通信は MCP で標準化する
4. AgentCore Gateway を中央統合ハブとして使用する
5. 適切な接続管理（タイムアウト、リトライ）を実装する
```

### ステップ 3.3: 段階的ロールアウト計画

```
Phase 1: Shadow Mode（1週間）
  - 本番トラフィックをシャドーイング
  - エージェント応答を記録するが返さない
  - 評価スコアを計測

Phase 2: Canary Release（2週間）
  - 5% のトラフィックをエージェントに流す
  - 人間のレビュー付き
  - メトリクス比較（人間 vs エージェント）

Phase 3: Gradual Rollout（4週間）
  - 25% → 50% → 75% → 100% と段階的に拡大
  - 各段階でメトリクスを確認
  - 問題発生時は即時ロールバック

Phase 4: Full Production
  - 100% エージェント対応
  - 継続的な評価と改善
  - 定期的な WA レビュー
```

---

## パート 4: まとめとコース全体の振り返り（5分）

### コースで学んだ技術の統合

| モジュール | 技術 | WA の柱 |
|-----------|------|---------|
| M01 | マルチエージェントパターン | 信頼性、パフォーマンス |
| M02 | コンテキストエンジニアリング | パフォーマンス、コスト |
| M03 | セキュリティ・コンプライアンス | セキュリティ |
| M04 | オブザーバビリティ・評価 | 運用上の優秀性 |
| M05 | Well-Architected 統合 | 全柱の統合 |

### 次のステップ

1. 自社のエージェンティック AI システムに WA レビューを実施
2. 最も優先度の高い改善領域を特定
3. 段階的に改善を実装（シンプルに開始して反復）
4. 定期的なレビューサイクルを確立

---

## 参考ドキュメント

- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [AWS Well-Architected Framework - Generative AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html)
- [Amazon Bedrock AgentCore - デプロイガイド](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime.html)
- [Amazon Bedrock AgentCore - FAQ](https://aws.amazon.com/bedrock/agentcore/faqs/)
- [Amazon Bedrock - セキュリティベストプラクティス](https://docs.aws.amazon.com/bedrock/latest/userguide/security-best-practices.html)
