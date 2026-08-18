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

### ステップ 1.3: CloudWatch Transaction Search の有効化（初回のみ）

AgentCore Observability を使用するためには、CloudWatch Transaction Search を有効化する必要があります（アカウントごとに 1 回）。

1. AWS コンソールで **CloudWatch** を開く
2. 左ナビゲーションペインの **Settings** を選択
3. **Transaction Search** セクションを確認
4. 有効になっていない場合は **Enable** をクリック
5. 有効化が完了するまで数分待機

### ステップ 1.4: トレーシングデモの実行

ADOT SDK 経由で実行するため、ラッパースクリプトを使います：

```bash
bash run_otel_tracing.sh
```

このスクリプトは以下を行います：
1. CloudWatch ロググループを作成
2. ADOT 用の環境変数をセット
3. `opentelemetry-instrument` コマンド経由でエージェントを実行（自動計装）
4. トレースデータが CloudWatch に送信される

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

## パート 2: CloudWatch ダッシュボードとアラーム（10分）

### ステップ 2.1: ダッシュボードとアラームの自動作成

以下のスクリプトを実行すると、カスタムメトリクスの送信・ダッシュボード作成・アラーム作成が一括で行われます：

```bash
python cloudwatch_dashboard.py
```

作成されるリソース：
- **ダッシュボード**: `AgenticAI-Observability`
- **アラーム**: `AgenticAI-HighLatency-P95` / `AgenticAI-HighErrorRate` / `AgenticAI-GuardrailSpike`
- **メトリクス**: `AgenticAI/CustomerSupport` ネームスペースに各エージェントのメトリクス

### ステップ 2.2: ダッシュボードの確認（コンソール）

1. AWS コンソールで **CloudWatch** を開く: https://console.aws.amazon.com/cloudwatch/
2. 左ナビゲーションペインで **Dashboards** を選択
3. **AgenticAI-Observability** をクリック
4. 以下のウィジェットが表示されていることを確認：
   - エージェント呼び出し回数（エージェント別）
   - レイテンシー P50/P95/P99
   - トークン消費量（Input/Output）
   - エラー率 & Guardrail 介入
   - タスク完了率
   - ツール呼び出し回数

### ステップ 2.3: アラームの確認（コンソール）

1. 左ナビゲーションペインで **Alarms** → **All alarms** を選択
2. `AgenticAI-` で始まるアラームが 3 つ作成されていることを確認：

   | アラーム名 | 条件 | 意味 |
   |-----------|------|------|
   | AgenticAI-HighLatency-P95 | P95 > 10,000ms | レイテンシー劣化 |
   | AgenticAI-HighErrorRate | ErrorRate > 5% | エラー率上昇 |
   | AgenticAI-GuardrailSpike | Guardrail > 10回/分 | セキュリティ異常 |

### ステップ 2.4: アラーム設計の考え方

| 観点 | 設計ポイント |
|------|------------|
| 閾値 | ベースライン + 余裕（ノイズ回避） |
| 評価期間 | 一時的なスパイクを除外（2-3 データポイント） |
| アクション | 本番では SNS → PagerDuty / Slack 連携 |
| Missing data | `notBreaching`（データなし = 正常扱い） |

### ステップ 2.5: （参考）手動でダッシュボードを作成する場合

1. CloudWatch コンソールで **Dashboards** → **Create dashboard**
2. **Dashboard name** を入力して **Create dashboard**
3. **Add widget** で **Line** を選択し **Next**
4. **Custom namespaces** → **AgenticAI/CustomerSupport** → **AgentName** からメトリクスを選択
5. **Graphed metrics** タブで **Statistic**（Sum/Average）と **Period**（1min/5min）を設定
6. **Create widget** をクリック
7. ウィジェットを追加する場合は **+** ボタンで繰り返し
8. 最後に **Save** をクリック

### ステップ 2.6: （参考）手動でアラームを作成する場合

1. CloudWatch コンソールで **Alarms** → **All alarms** → **Create alarm**
2. **Select metric** → **Custom namespaces** → **AgenticAI/CustomerSupport** → **AgentName**
3. 対象メトリクス（例: `Latency_P95`）を選択して **Select metric**
4. **Conditions** を設定：
   - **Threshold type**: Static
   - **Whenever metric is...**: Greater than
   - **than...**: 閾値を入力（例: `10000`）
5. **Next** → **Notification** を設定（本番では SNS トピックを指定）
6. **Next** → **Alarm name** と **Description** を入力
7. **Create alarm** をクリック

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

## パート 3.5: AgentCore オンライン評価（Runtime エンドポイント対象）（10分）

### ステップ 3.5.1: オンライン評価の概要

AgentCore Evaluations の「オンライン評価」は、AgentCore Runtime エンドポイントのライブトラフィックを自動サンプリングし、組み込みエバリュエーターで継続的に品質を評価する仕組みです。

| 項目 | 内容 |
|------|------|
| データソース | AgentCore Runtime のトレース（CloudWatch Logs） |
| 実行方式 | 継続的・自動（設定後は人手不要） |
| サンプリング | 0.01% - 100% で設定可能 |
| セッション検出 | アイドルタイムアウト（1-60分）で自動判定 |
| 結果出力 | CloudWatch メトリクス（Embedded Metric Format） |
| アラーム連携 | CloudWatch Alarms と直接統合可能 |

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AgentCore      │────▶│  CloudWatch Logs  │────▶│  Online         │
│  Runtime        │     │  (トレーススパン) │     │  Evaluation     │
│  Endpoint       │     │                    │     │  (自動サンプル) │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  CloudWatch     │
                                                  │  Metrics/Alarms │
                                                  └─────────────────┘
```

### ステップ 3.5.2: オンライン評価のセットアップ

以下のスクリプトを実行すると、IAM ロールの作成とオンライン評価設定が一括で行われます：

```bash
python online_evaluation.py
```

このスクリプトは以下を実行します：
1. AgentCore Runtime にデプロイ済みのエージェントを検出（なければ ADOT デモのロググループを使用）
2. 評価実行用の IAM ロールを作成（`AgentCoreOnlineEvaluationRole`）
3. オンライン評価設定を作成（サンプリング率 100%、セッションタイムアウト 5 分）
4. 結果確認方法のガイダンスを表示

### ステップ 3.5.3: 使用するエバリュエーター

スクリプトでは以下の 4 つの組み込みエバリュエーターを設定しています：

| エバリュエーター | 説明 |
|----------------|------|
| Builtin.Helpfulness | 回答がユーザーにとってどれだけ有用か |
| Builtin.Correctness | 回答が事実に基づいて正確か |
| Builtin.GoalSuccessRate | ユーザーの目標が達成されたか（エンドツーエンド） |
| Builtin.ToolSelectionAccuracy | エージェントが適切なツールを選択したか |

> ℹ️ 組み込みエバリュエーターは最大 10 個まで設定可能です。カスタムエバリュエーター（Lambda 関数）も混在できます。

### ステップ 3.5.4: 評価をトリガーする

オンライン評価は設定後に自動実行されますが、評価対象のトレースが必要です。パート 1 の ADOT デモを再実行して評価をトリガーします：

```bash
bash run_otel_tracing.sh
```

評価結果が表示されるまで 5-10 分かかります。

### ステップ 3.5.5: 評価結果の確認（コンソール）

1. AWS コンソールで **CloudWatch** を開く
2. **GenAI Observability** → **Bedrock AgentCore** を選択
3. **Evaluations** タブを確認
4. セッション毎のスコア（Helpfulness, Correctness 等）を確認

### ステップ 3.5.6: 本番環境での推奨設定

| パラメータ | デモ設定 | 本番推奨 | 理由 |
|-----------|---------|---------|------|
| samplingPercentage | 100% | 1-10% | コスト最適化 |
| sessionTimeoutMinutes | 5 | 15 | セッション完了を正確に検出 |
| enableOnCreate | True | True | 即座に監視開始 |
| evaluators | 4 個 | 5-8 個 | カスタム評価も追加 |

**アラーム連携の例（品質劣化の自動検出）:**

```
メトリクス: Bedrock-AgentCore/Evaluations
  → EvaluatorName = "Builtin.Helpfulness"
  → avg(score) < 3.5 が 3 データポイント連続
  → SNS → Slack / PagerDuty 通知
```

---

## パート 4: エージェント評価スクリプトの実行（5分）

### ステップ 4.1: カスタムエバリュエーターの実行

コンソールの組み込み評価に加えて、業務固有のカスタム評価基準でも評価を行います：

```bash
python agent_evaluation.py
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
