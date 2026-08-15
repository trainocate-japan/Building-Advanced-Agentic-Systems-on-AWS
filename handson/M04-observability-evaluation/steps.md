# モジュール 4: 本番環境のモニタリング、オブザーバビリティ、評価 - ハンズオン手順

## パート 1: OpenTelemetry 分散トレーシング（10分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M04-observability-evaluation
```

### ステップ 1.2: トレーシングの概要

エージェントのオブザーバビリティには 2 つのレベルがあります：

| レベル | 計測対象 | 例 |
|-------|---------|---|
| **トレースレベル** | エージェント実行全体 | 全体レイテンシー、総トークン数、成功/失敗 |
| **スパンレベル** | 個々のステップ | LLM 呼び出し時間、ツール実行時間、各ステップのトークン数 |

### ステップ 1.3: トレーシングデモの実行

```bash
python3.12 otel_tracing.py
```

出力を確認し、以下を議論します：
- トレース全体の構造（親スパン → 子スパン）
- LLM 呼び出しスパンがレイテンシーの大部分を占めること（~69%）
- ツール実行時間のボトルネック特定

### ステップ 1.4: AgentCore Observability の確認（コンソール）

AgentCore Observability は CloudWatch の GenAI Observability ページに統合されています。

1. AWS コンソールで **Amazon CloudWatch** を開く: https://console.aws.amazon.com/cloudwatch/
2. 左ナビゲーションペインで **GenAI Observability** → **Bedrock AgentCore** を選択
3. **Agents** タブを確認

表示される情報：
- **Agent name**: エージェント名
- **Sessions**: セッション数
- **Traces**: トレーススパン（推論とモデル呼び出し）
- **Span details**: `invoke_agent`, `chat`, `execute_event_loop_cycle` 等のスパンとレイテンシー・トークンメトリクス

> ℹ️ AgentCore Observability を初めて使用する場合は、CloudWatch Transaction Search を有効化する必要があります（アカウントごとに 1 回のセットアップ）。

### ステップ 1.5: スパン属性の理解

| 属性 | 説明 | 例 |
|------|------|---|
| `gen_ai.system` | AI システム名 | `aws.bedrock` |
| `gen_ai.request.model` | モデル ID | `us.amazon.nova-pro-v1:0` |
| `gen_ai.usage.input_tokens` | 入力トークン数 | `150` |
| `gen_ai.usage.output_tokens` | 出力トークン数 | `300` |
| `gen_ai.response.finish_reasons` | 終了理由 | `["end_turn"]` |

---

## パート 2: CloudWatch ダッシュボード構築（コンソール操作）（15分）

### ステップ 2.1: カスタムメトリクスの送信

まずエージェントのメトリクスデータを送信します：

```bash
python3.12 cloudwatch_dashboard.py
```

これにより、`AgenticAI/CustomerSupport` ネームスペースにカスタムメトリクスが送信されます。

### ステップ 2.2: CloudWatch ダッシュボードの作成（コンソール）

1. AWS コンソールで **CloudWatch** を開く: https://console.aws.amazon.com/cloudwatch/
2. 左ナビゲーションペインで **Dashboards** を選択
3. **Create dashboard** をクリック
4. **Dashboard name**: `AgenticAI-Observability` と入力
5. **Create dashboard** をクリック

### ステップ 2.3: ウィジェットの追加 - エージェント呼び出し回数

1. **Add widget** ダイアログで **Line** を選択し、**Next** をクリック
2. **Metrics** タブで以下を選択：
   - **Custom namespaces** → **AgenticAI/CustomerSupport** → **AgentName** を選択
   - `InvocationCount` メトリクスのチェックボックスを ON（全エージェント分）
3. **Graphed metrics** タブに切り替え：
   - **Statistic**: `Sum`
   - **Period**: `1 minute`
4. **Create widget** をクリック

### ステップ 2.4: ウィジェットの追加 - レイテンシー

1. ダッシュボード画面で **+** (Add widget) をクリック
2. **Line** を選択
3. **Custom namespaces** → **AgenticAI/CustomerSupport** → **AgentName**
4. `orchestrator` の `Latency_P50`, `Latency_P95`, `Latency_P99` を選択
5. **Graphed metrics** タブ：
   - **Statistic**: `Average`
   - **Period**: `1 minute`
6. **Create widget** をクリック

### ステップ 2.5: ウィジェットの追加 - トークン消費量

1. **+** → **Line** を選択
2. `orchestrator` の `InputTokens`, `OutputTokens` を選択
3. **Statistic**: `Sum`, **Period**: `5 minutes`
4. **Create widget** をクリック

### ステップ 2.6: ウィジェットの追加 - エラー率

1. **+** → **Number** を選択
2. `orchestrator` の `ErrorRate` を選択
3. **Statistic**: `Average`, **Period**: `5 minutes`
4. **Create widget** をクリック

### ステップ 2.7: ダッシュボードの保存

1. 画面右上の **Save** をクリック
2. ウィジェットをドラッグ & リサイズして見やすくレイアウト調整
3. 再度 **Save** をクリック

### ステップ 2.8: アラームの作成（コンソール）

**高レイテンシーアラーム:**

1. CloudWatch コンソールの左メニューから **Alarms** → **All alarms** を選択
2. **Create alarm** をクリック
3. **Select metric** をクリック
4. **Custom namespaces** → **AgenticAI/CustomerSupport** → **AgentName** → `orchestrator` の `Latency_P95` を選択
5. **Select metric** をクリック
6. **Conditions** を設定：
   - **Threshold type**: Static
   - **Whenever Latency_P95 is...**: Greater than
   - **than...**: `10000`（10秒 = 10000ms）
7. **Next** をクリック
8. **Notification** セクション：
   - 今回は **Remove** で通知をスキップ（本番では SNS トピックを設定）
9. **Next** をクリック
10. **Alarm name**: `AgenticAI-HighLatency-P95`
11. **Description**: `P95 レイテンシーが 10 秒を超過`
12. **Create alarm** をクリック

**高エラー率アラーム:**

同様の手順で以下を作成：
- **Metric**: `ErrorRate` (orchestrator)
- **Condition**: Greater than `5`
- **Alarm name**: `AgenticAI-HighErrorRate`
- **Description**: `エラー率が 5% を超過`

---

## パート 3: Bedrock モデル評価ジョブの実行（コンソール操作）（15分）

### ステップ 3.1: 評価データセットの準備

評価データセットを S3 にアップロードします：

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET="handson-agentic-assets-${ACCOUNT_ID}"

aws s3 cp evaluation-dataset.jsonl s3://$BUCKET/evaluation/evaluation-dataset.jsonl
echo "アップロード完了: s3://$BUCKET/evaluation/evaluation-dataset.jsonl"
```

### ステップ 3.2: Automatic: LLM-as-a-Judge 評価の実行（コンソール）

1. **Amazon Bedrock** コンソールを開く
2. 左ナビゲーションペインの **Inference and assessment** → **Evaluations** を選択
3. **Model evaluations** ペインで **Create** をクリックし、**Automatic: LLM-as-a-judge** を選択

4. **Model evaluation details** を入力：
   - **Evaluation name**: `m04-agent-quality-eval`
   - **Description**: `Module 4 ハンズオン - エージェント品質評価`

5. **Evaluator model**（審査員モデル）を選択：
   - **Select model** をクリック
   - **Amazon Nova Pro** を選択
   - **Apply** をクリック

6. **Inference source** を設定：
   - **Select source**: **Bedrock models** を選択
   - **Select model** をクリック
   - 評価対象モデルとして **Amazon Nova Lite** を選択
   - **Apply** をクリック

7. **Metrics** を選択（評価基準）：

   以下のメトリクスにチェックを入れます：

   | メトリクス | 説明 |
   |-----------|------|
   | **Helpfulness** | 回答がどれだけ有用で包括的か |
   | **Correctness** | 回答がどれだけ正しいか |
   | **Faithfulness** | 元の情報との整合性 |
   | **Harmfulness** | 有害コンテンツを避けているか |

8. **Datasets** を設定：
   - **Choose a prompt dataset**: **Browse S3** をクリック
   - `handson-agentic-assets-<ACCOUNT_ID>/evaluation/evaluation-dataset.jsonl` を選択

9. **Evaluation results** の出力先を設定：
   - S3 URI: `s3://handson-agentic-assets-<ACCOUNT_ID>/evaluation/results/`

10. **IAM service role**:
    - **Create a new role** を選択（自動で必要な権限が付与されます）

11. **Create** をクリック

### ステップ 3.3: 評価ジョブの監視

1. **Evaluations** ページに戻ると、ジョブが **In Progress** と表示される
2. 完了まで数分〜十数分待機

### ステップ 3.4: 評価結果の確認（コンソール）

ジョブが **Complete** になったら：

1. ジョブ名をクリックして詳細を表示
2. **Metrics summary** を確認：
   - 各メトリクスのスコア（例: Helpfulness 0.83, Correctness 1.00 等）
3. **Generation metrics details** セクションで個別メトリクスの内訳を確認
4. **Prompt details** をクリックして各レコードの詳細を確認：
   - Prompt input（入力）
   - Generation output（生成された回答）
   - Ground truth（期待される回答）
   - Individual scores（個別スコア）
   - スコアにホバーすると詳細な説明が表示される

### ステップ 3.5: 評価結果の考察

| 観点 | 確認ポイント |
|------|------------|
| 低スコアのケース | なぜ低スコアになったか？プロンプト改善が必要か？ |
| カテゴリ別の傾向 | 特定カテゴリ（billing, technical等）で品質差があるか？ |
| 改善アクション | システムプロンプトの修正？ツールの追加？知識ベースの更新？ |

---

## パート 4: エージェント評価スクリプトの実行（5分）

### ステップ 4.1: カスタムエバリュエーターの実行

コンソールの組み込み評価に加えて、業務固有のカスタム評価基準でも評価を行います：

```bash
python3.12 agent_evaluation.py
```

このスクリプトは以下のカスタムエバリュエーターを実行します：
- **Helpfulness**: 回答の有用性（LLM as a Judge）
- **Faithfulness**: ハルシネーション検出
- **Disclaimer Check**: 免責事項の有無（プログラマティック）
- **Response Structure**: 回答構造の品質

### ステップ 4.2: 結果の確認

出力されるサマリーテーブルを確認し、以下を議論：
- 組み込みエバリュエーター vs カスタムエバリュエーターの使い分け
- 業務固有の評価基準（免責事項チェック等）の設計方法
- 継続的改善のための評価パイプライン

---

## パート 5: ディスカッション（5分）

### 3 ステージ評価モデル

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   計測      │────▶│   判断      │────▶│  インサイト  │
│  (Measure)  │     │  (Judge)    │     │  (Insight)  │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ メトリクス   │     │ スコアリング │     │ トレンド分析 │
│ 収集        │     │             │     │ 根本原因     │
└─────────────┘     └─────────────┘     └─────────────┘
```

### オブザーバビリティ設計のベストプラクティス

1. **最初からオブザーバビリティを組み込む**: 後付けは困難
2. **すべての統合ポイントをトレース**: LLM、ツール、外部 API
3. **ビジネスメトリクスと技術メトリクスを統合**: 品質スコア + レイテンシー
4. **アラートの適切な閾値設定**: ノイズを避けつつ重要な問題を検出
5. **評価データセットの継続的更新**: 本番の失敗ケースを評価セットに追加

### 品質劣化の検出と対応

| 指標 | 正常範囲 | 劣化の兆候 | 対応 |
|------|---------|-----------|------|
| Helpfulness | 4.0+ | < 3.5 | プロンプト見直し |
| Task Completion | 90%+ | < 80% | ツール/知識ベース更新 |
| Latency P95 | < 5s | > 10s | モデル変更/キャッシュ追加 |
| Error Rate | < 2% | > 5% | エラーログ調査 |

---

## 参考ドキュメント

- [Amazon Bedrock AgentCore Observability - 概要](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html)
- [Amazon Bedrock AgentCore - サービス提供オブザーバビリティデータ](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-service-provided.html)
- [Amazon Bedrock - モデル評価ジョブの作成](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-jobs-management-create.html)
- [Amazon Bedrock - 組み込みメトリクスによるモデル評価](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-built-in-metrics.html)
- [Amazon CloudWatch - ダッシュボードの作成](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/create_dashboard.html)
- [Amazon CloudWatch - 静的閾値に基づくアラームの作成](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html)
- [AgentCore Observability でオンプレミス・マルチクラウドエージェントを監視 (Blog)](https://aws.amazon.com/blogs/machine-learning/monitor-on-premises-and-multi-cloud-ai-agents-with-agentcore-observability/)
- [LLM-as-a-judge on Amazon Bedrock Model Evaluation (Blog)](https://aws.amazon.com/blogs/machine-learning/llm-as-a-judge-on-amazon-bedrock-model-evaluation/)
