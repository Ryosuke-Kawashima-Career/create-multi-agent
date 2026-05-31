# 実装手順 (Dynamic Travel Planning Agent)

ADK 2.1 の Graph Workflow と A2A specialist agents を使って「旅行計画 AI エージェント」を組み立てます。完成形は `agents/` ディレクトリ全体です。

> 参考: 完成済みのコードは `create-multi-agent/repos/example/` にあります。詰まったら該当ファイルを覗いてください。本手順では「example の同名ファイルを参照」と書いてある箇所はコピーで構いません。

---

## アーキテクチャ概要

```text
Coordinator Workflow (port 8100)
  └─ capture_user_query
  └─ clarify_agent              # TravelRequest に構造化
  └─ route_after_clarification  # 不足あれば RequestInput で再質問 (最大2回)
  └─ strategist_agent           # TravelOption を 3〜5 案生成
  └─ travel_research_workflow   # 候補ごとに google_search で fan-out / fan-in
  └─ evaluation_agent           # AgentTool で 3 specialist 呼び出し → 統合推薦
  │    ├─ comfort_agent    (RemoteA2aAgent, port 8101)
  │    ├─ risk_agent       (RemoteA2aAgent, port 8102)
  │    └─ experience_agent (RemoteA2aAgent, port 8103)
  └─ request_user_selection     # 上位3案を提示し、選択 or 再提案
  └─ planner_agent              # 詳細旅程 markdown 生成
  └─ illustrator_prompt_agent   # 旅しおり画像 prompt 生成
  └─ illustrator_agent          # gemini-3-pro-image で画像生成
```

`session.state` に `travel_request` → `travel_options` → `research_reports` → `coordinator_recommendation` → `selected_option_id` → `selected_option_context` → `itinerary_markdown` → `illustrator_prompt` を順に貯めていきます。

---

## Step 0. 環境セットアップ

1. Cloud Shell またはローカルで本リポジトリのルートに移動します。
2. setup スクリプトを実行し、connpass ID を入力します。

   ```bash
   ./scripts/setup.sh
   ```

   `.env` が生成され、Google Cloud Project ID には固定値 `create-multi-agent` が設定されます。`uv sync --extra dev` で依存関係が入ります。
3. 認証を確認します。

   ```bash
   gcloud auth application-default login
   gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
   ```

✅ `uv run python -c "import google.adk; print(google.adk.__version__)"` が動けば OK。

---

## Step 1. プロジェクト骨格と共通ヘルパー

最小限のファイルを置きます。example の同名ファイルをコピーで構いません。

- `pyproject.toml` / `Makefile` / `.env.example` — 依存定義とビルドコマンド。
- `agents/__init__.py` — 空ファイル。
- `agents/_common.py` — 以下の共通ヘルパー:
  - `ensure_repo_path()` — `sys.path` にリポジトリルートを追加し、`uvicorn agents.xxx.agent:app` から `from agents...` 形式で import できるようにする。
  - `load_dotenv(REPO_ROOT / ".env")` — `.env` を読む。
  - `remote_agent_card_url(env_name, default_base_url)` — `/.well-known/agent-card.json` / `/v1/card` URL を正規化。
  - `GoogleCloudAuth` (httpx.Auth) + `runtime_a2a_httpx_client()` — Vertex AI Agent Runtime にデプロイした specialist と通信する際に ADC トークンを付与。
  - `to_a2a_app(agent, default_port)` — ADK Agent を A2A ASGI アプリへ変換。

✅ `make lint` が通る。

---

## Step 2. Clarify Agent

`agents/coordinator/clarify_models.py` と `agents/coordinator/clarify.py` を作ります。**まず clarify だけ動く最小 Workflow として `agent.py` も更新します。**

### clarify_models.py

```python
class TravelRequest(BaseModel):
    origin: str | None
    duration: str | None
    budget: str | None
    transport: str | None
    companions: str | None
    preferences: list[str]
    constraints: list[str]
    unknowns: list[str]   # 品質に影響する不足情報のみ
    raw_user_query: str
```

### clarify.py

- `clarify_agent: Agent` — `output_schema=TravelRequest`, `mode="single_turn"`. instruction で origin / duration / budget / transport の不足のみ `unknowns` に入れるよう指示。推測で補える軽微な項目は入れすぎない。
- `capture_user_query(ctx, node_input)` — 生入力を `state["raw_user_query"]` に保存、`clarification_rounds` を 0 で初期化。
- `route_after_clarification(ctx, node_input: TravelRequest)` — `unknowns` に重要な項目（origin / duration / budget / transport / 出発 / 期間 / 予算 / 交通）があり rounds < 2 なら `Event(route=ROUTE_CLARIFY)`、それ以外は `DEFAULT_ROUTE`。
- `request_clarification(ctx, node_input)` — `RequestInput(message, payload, response_schema=str)` を yield。
- `build_reclarify_input(ctx, node_input)` — 元の希望 + 前回の構造化結果 + 追加回答を連結して clarify_agent に再投入。

### agent.py（この時点）

```python
root_agent = Workflow(
    name="dynamic_travel_planning_agent",
    edges=[
        ("START", capture_user_query, clarify_agent),
        (route_after_clarification, {
            ROUTE_CLARIFY: request_clarification,
            DEFAULT_ROUTE: ???,  # 次ステップで埋める
        }),
        (request_clarification, build_reclarify_input, clarify_agent),
        (clarify_agent, route_after_clarification),
    ],
)
app = to_a2a_app(root_agent, default_port=8100)
```

`DEFAULT_ROUTE` の先はまだ `clarify_agent` をダミーで置いておくか、後述の `candidate_workflow` を追加してから繋ぎます。

✅ `make run` 後、ADK Web で `dynamic_travel_planning_agent` を選び「週末に一泊二日で温泉に行きたいです」と入力。出発地・予算・交通手段の質問が来れば OK。

---

## Step 3. Strategist と Research の Fan-out / Fan-in

`agents/coordinator/candidates_models.py` と `agents/coordinator/candidates.py` を作り、`agent.py` に strategist → research フェーズを追加します。

### candidates_models.py

```python
class TravelOption(BaseModel):
    option_id: str       # 例: "option_1" (安定した値)
    title: str
    destination: str
    concept: str
    research_focus: list[str]
    fit_hypothesis: str

class TravelOptions(BaseModel):
    options: list[TravelOption]   # 3〜5 案

class ResearchReport(BaseModel):
    option_id: str
    destination_summary: str
    access: str
    estimated_cost: str
    lodging_area: str
    recommended_spots: list[str]
    food_options: list[str]
    risks: list[str]
    weather_or_season_notes: list[str]
    source_notes: list[str]
    suitability_reason: str
```

### candidates.py

- `strategist_agent: Agent` — `output_schema=TravelOptions`. `option_id` は `option_1`, `option_2` のように安定した値を強制。
- `research_agent: Agent` — `tools=[google_search]`. **structured output と google_search は同時に使えない**ので構造化せず自然文の調査メモを返す。
- `research_report_formatter: Agent` — `output_schema=ResearchReport`. 調査メモを構造化。新規事実を断定せず不明項目は「要確認」と書く。
- `store_travel_options(ctx, node_input: TravelOptions)` — `state["travel_options"]` に保存して返す。
- `research_candidate(ctx, option)` — `@node(rerun_on_resume=True)` を付け、`research_agent` → `research_report_formatter` の 2 段直列で 1 候補を処理。
- `travel_research_workflow(ctx, node_input)` — `@node(rerun_on_resume=True)` を付け、`ctx.run_node(research_candidate, option)` を `asyncio.gather` で全候補並列実行。`collect_research_reports` で `state["research_reports"]`（`option_id` keyed dict）に格納して返す。

> **なぜ state に貯めるか**: 後で planner に渡す `SelectedOptionContext` が「選ばれた option だけ」を取り出すため。会話履歴に依存させると候補ごとの研究結果が混ざる。

### agent.py（この時点）

`candidate_workflow` を追加し、`DEFAULT_ROUTE: candidate_workflow` で接続します。`candidate_workflow` の edges は strategist → research まで（evaluation 以降は次ステップで追加）。

```python
candidate_workflow = Workflow(
    name="travel_candidate_workflow",
    edges=[
        ("START", strategist_agent, store_travel_options, travel_research_workflow),
        # evaluation 以降は次ステップで追加
    ],
)
```

✅ `make run` 後、明確な依頼（東京から一泊二日で温泉…）を入力し、`session.state` に `research_reports` が option_id ごとに入ることを ADK Web の Inspector で確認。

---

## Step 4. Specialist Agents を A2A サービスとして起動

3 つの specialist は別プロセスで動かし、coordinator からは `RemoteA2aAgent` で呼び出します。

### agents/{comfort,risk,experience}/agent.py

それぞれ `__init__.py` も作成します。

- `agents/comfort/agent.py` — `name="comfort_agent"`, `mode="chat"`, port 8101. 移動負荷・休憩・宿泊快適性・疲労しにくさを評価する instruction。`EvaluationReport` を返す。
- `agents/risk/agent.py` — port 8102. 休業・混雑・天候・予約困難・交通遅延・不確実性を評価。
- `agents/experience/agent.py` — port 8103. 非日常性・記憶に残る体験・嗜好一致を評価。

3 エージェント共通の instruction パターン:

```
あなたは <name>_agent です。
初回評価では EvaluationReport を返してください。
候補ごとの評価は option_evaluations に option_id, score (1-10), comment, concerns を入れてください。
<評価軸の説明>
Revision を求められた場合は RevisionReport を返し、修正不要なら revision_note に 'no change' と明記してください。
```

`evaluation_models.py` を作ります:

```python
class OptionEvaluation(BaseModel):
    option_id: str
    score: int   # 1-10
    comment: str
    concerns: list[str]

class EvaluationReport(BaseModel):
    agent_name: str
    preferred_option_id: str
    option_evaluations: list[OptionEvaluation]
```

✅ `make run-specialists` 後、別ターミナルで `curl http://localhost:8101/.well-known/agent-card.json` が JSON を返す。

---

## Step 5. Multi-Agent Evaluation

`agents/coordinator/evaluation.py` を作り、`candidate_workflow` に evaluation フェーズを追加します。

### evaluation.py

- `comfort_agent / risk_agent / experience_agent: RemoteA2aAgent` — `agent_card=remote_agent_card_url("COMFORT_A2A_URL", "http://localhost:8101")`, `output_schema=EvaluationReport`, `httpx_client=runtime_a2a_httpx_client()`。
- `evaluation_agent: Agent` — `output_schema=CoordinatorRecommendation`, `tools=[AgentTool(comfort_agent), AgentTool(risk_agent), AgentTool(experience_agent)]`. instruction で「3 specialist に分析を依頼 → 費用分析 → 不足・矛盾あれば再依頼 → 統合して ranked_options 最大 3 案を返す」を指示。
- `build_evaluation_input(ctx, node_input)` — `TravelRequest` + `TravelOptions` + `ResearchReports` をテキストで連結して返す。

`recommendation_models.py` も作ります:

```python
class RankedOption(BaseModel):
    option_id: str
    rank: int
    title: str
    reason: str
    cautions: list[str]

class CoordinatorRecommendation(BaseModel):
    ranked_options: list[RankedOption]   # 最大3
    comparison_summary: str
    conflict_resolution: str
    user_message: str
```

### agent.py（この時点）

`candidate_workflow` の edges に `build_evaluation_input, evaluation_agent, store_recommendation` を追加します（`store_recommendation` は次ステップで実装）。

✅ `make run`（specialists + coordinator + ADK Web）後、フルクエリを送り `coordinator_recommendation` が state に入ることを確認。

---

## Step 6. User Selection と Replan 分岐

`agents/coordinator/recommendation.py` を作り、ユーザーへの選択提示と分岐を実装します。`agent.py` も更新します。

### recommendation.py（前半）

- `store_recommendation(ctx, node_input: CoordinatorRecommendation)` — `state["coordinator_recommendation"]` に保存して返す。
- `planner_agent: Agent` — `gemini-3.5-flash`, `mode="single_turn"`. 選ばれた候補だけで詳細旅程 markdown を出力。
- `request_user_selection(ctx, node_input: CoordinatorRecommendation)` — `ranked_options[:3]` + 「4. 条件を変えて再提案」を並べ `RequestInput(response_schema=str | int)` を yield。
- `route_user_selection(ctx, node_input)` — 「4」や「再提案」「変えて」を含めば `ROUTE_REPLAN`、それ以外は rank 番号 / option_id / title でマッチし `state["selected_option_id"]` をセットして `ROUTE_SELECTED`。
- `build_replan_input(ctx, node_input)` — 現在の TravelRequest + 推薦 + 変更希望を連結して clarify_agent に再投入するテキストを返す。

### agent.py（この時点）

```python
candidate_workflow = Workflow(
    name="travel_candidate_workflow",
    edges=[
        ("START", ..., evaluation_agent, store_recommendation,
         request_user_selection, route_user_selection),
        (route_user_selection, {
            ROUTE_SELECTED: build_planner_input,   # 次ステップで実装
            ROUTE_REPLAN: build_replan_input,
        }),
        (build_replan_input, clarify_agent),
    ],
)
```

✅ `make run` 後、上位 3 案の提示と「4. 条件を変えて再提案」が表示されることを確認。「4」を入力すると条件変更ループに入ることも確認。

---

## Step 7. Planner — 詳細旅程生成

`recommendation.py` に planner 周りのノードを追加し、`agent.py` に planner フェーズを追加します。

### recommendation.py（後半）

- `build_planner_input(ctx, node_input)` — `build_selected_option_context` を呼んで `SelectedOptionContext` を組み立て、planner に渡す Markdown 文字列を返す。**state 全体ではなく選ばれた option だけを渡す**のがポイント。
- `store_itinerary_markdown(ctx, node_input)` — `state["itinerary_markdown"]` に保存。

`SelectedOptionContext` モデルも `recommendation_models.py` に追加:

```python
class SelectedOptionContext(BaseModel):
    travel_request: TravelRequest
    selected_option: TravelOption
    research_report: ResearchReport
    evaluations: list[EvaluationReport]
    recommendation: RankedOption | None
    coordinator_notes: str
```

### agent.py（この時点）

```python
(build_planner_input, planner_agent, store_itinerary_markdown),
```

✅ `make run` 後、候補を選択すると `itinerary_markdown` が state に入ることを確認。

---

## Step 8. Illustrator — 旅しおり画像生成

`agents/coordinator/illustrator.py` を作り、`agent.py` に illustrator フェーズを追加します。

### illustrator.py

- `illustrator_prompt_agent: Agent` — `gemini-3.1-pro-preview`, `mode="single_turn"`. 旅程 markdown から旅しおり表紙画像の英語 prompt を生成。スタイル指示は固定:

  ```
  flat 2D cel-shaded anime illustration, hand-drawn line art, crisp black outlines,
  minimal gradients, no realistic skin texture, no 3D rendering,
  no photorealistic lighting, no glossy highlights, no cinematic color grading
  ```

  `recommendation_prompts.py` の `IMAGE_PROMPT_FORMAT` を instruction に埋め込む。

- `illustrator_agent: Agent` — `gemini-3-pro-image`, `mode="single_turn"`. prompt をそのまま画像化。

### agent.py（この時点、完成形）

```python
(
    build_planner_input,
    planner_agent,
    store_itinerary_markdown,
    illustrator_prompt_agent,
    illustrator_agent,
),
```

✅ `make run` 後、候補を選択すると旅しおり画像が生成されることを確認。

---

## 動作確認クエリ

`QUERY.md` のサンプルを使って 3 シナリオを試します。

| シナリオ | 入力例 | 期待動作 |
|---------|--------|---------|
| 明確な依頼 | 「東京から一泊二日で、静かな田舎に行きたいです。公共交通で行けて、温泉があると嬉しいです。予算は3万円以内です。」 | clarification なしで候補生成 → 上位3案提示 → 選択 → 旅程 + 画像 |
| 情報不足 | 「週末に一泊二日で温泉に行きたいです。」 | RequestInput で出発地・予算・交通手段を質問 (最大2回) → 回答後に通常フロー |
| 再提案 | 選択画面で「4. 条件を変えて再提案。海が見える場所を優先してください。」 | TravelRequest 更新 → 新しい候補で再ループ |

ADK Web の Inspector で各ステップ後に state を確認し、`travel_request` → `travel_options` → `research_reports` → `coordinator_recommendation` → `selected_option_id` → `itinerary_markdown` の順で埋まることを確認します。

---

## Step 9. Agent Runtime へのデプロイ（任意）

```bash
./scripts/deploy_all.sh
```

specialist 3 つを Agent Runtime にデプロイし、coordinator の環境変数（`COMFORT_A2A_URL` 等）に Reasoning Engine の A2A card URL を注入してから coordinator をデプロイします。`TRAVEL_AGENT_A2A_USE_ADC_AUTH=true` を `.env` に追加すると `runtime_a2a_httpx_client()` が ADC トークン付きの httpx client を返し、specialist と認証付きで通信できます。

```bash
# 削除
./scripts/cleanup_all.sh --dry-run
./scripts/cleanup_all.sh
```

---

## トラブルシューティング

- **`google_search` で structured output が返らない** — 仕様上 tool と structured output は両立不可。`research_agent` は自然文を返し、`research_report_formatter` で構造化する 2 段構成にする。
- **specialist に `connection refused`** — `make run` は specialists + coordinator + ADK Web を同時起動するので、specialist 側の起動完了前に coordinator がリクエストすることがある。coordinator を少し遅れて起動するか、`make run-specialists` 後に別で `make run-coordinator` & `make web` を実行。
- **`state["research_reports"]` に option が欠ける** — `research_agent` の instruction に「`option_id` を必ず維持すること」を強調する。
- **clarification が 2 回以上発生する** — `route_after_clarification` で判定する `material_unknowns` のキーワードが広すぎると毎回ループする。origin / duration / budget / transport に限定すること。
- **planner が全候補の情報を混ぜる** — `build_planner_input` で state 全体ではなく `SelectedOptionContext`（選ばれた option 分のみ）を渡しているか確認する。
