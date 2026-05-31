from __future__ import annotations
from typing import Any
from google.adk.agents.context import Context
from google.adk.events import RequestInput
from google.adk.events.event import Event
from agents.coordinator.planner_models import CoordinatorRecommendation
from agents.coordinator.utils import text
from agents.coordinator.clarify import STATE_TRAVEL_REQUEST
from google.adk import Agent
from agents.coordinator.candidates import STATE_RESEARCH_REPORTS, STATE_TRAVEL_OPTIONS
from agents.coordinator.candidates_models import ResearchReport, TravelOption
from agents.coordinator.clarify_models import TravelRequest
from agents.coordinator.planner_models import SelectedOptionContext
STATE_COORDINATOR_RECOMMENDATION = "coordinator_recommendation"
ROUTE_REPLAN = "replan"
ROUTE_SELECTED = "selected"
MAX_USER_VISIBLE_OPTIONS = 3
STATE_SELECTED_OPTION_ID = "selected_option_id"
PLANNER_AGENT_MODEL = "gemini-3.5-flash"
STATE_SELECTED_OPTION_CONTEXT = "selected_option_context"
STATE_ITINERARY_MARKDOWN = "itinerary_markdown"
planner_agent = Agent(
    name="planner",
    model=PLANNER_AGENT_MODEL,
    description="選ばれた候補だけを使って詳細な旅程をmarkdownで作る。",
    instruction=(
        "入力: 選択された旅行候補\n"
        "出力: 詳細旅程のmarkdown"
        "読みやすさを優先し、見出し、箇条書き、時間帯ごとの流れを自然に使います。"
        "日程には移動、食事、宿泊、雨天代替、注意点を含めてください。"
        "入力にない情報は断定せず「要確認」と書いてください。"
    ),
    mode="single_turn",
)
def store_recommendation(
    ctx: Context,
    node_input: CoordinatorRecommendation,
) -> CoordinatorRecommendation:
    ctx.state[STATE_COORDINATOR_RECOMMENDATION] = node_input.model_dump()
    return node_input
def store_recommendation(
    ctx: Context,
    node_input: CoordinatorRecommendation,
) -> CoordinatorRecommendation:
    ctx.state[STATE_COORDINATOR_RECOMMENDATION] = node_input.model_dump()
    return node_input


def request_user_selection(ctx: Context, node_input: CoordinatorRecommendation):
    ranked = node_input.ranked_options[:MAX_USER_VISIBLE_OPTIONS]
    lines = [f"{item.rank}. {item.title} - {item.reason}" for item in ranked]
    lines.append("4. 条件を変えて再提案")
    message_parts = []
    if node_input.user_message:
        message_parts.append(node_input.user_message)
    message_parts.append("どの案で詳細旅程を作りますか。\n" + "\n".join(lines))
    yield RequestInput(
        message="\n\n".join(message_parts),
        payload={"ranked_options": [item.model_dump() for item in ranked]},
        response_schema=str | int,
    )

def route_user_selection(ctx: Context, node_input: Any):
    response = text(node_input)
    if response.startswith("4") or "再提案" in response or "変えて" in response:
        yield Event(route=ROUTE_REPLAN, output=response)
        return

    recommendation = CoordinatorRecommendation.model_validate(
        ctx.state[STATE_COORDINATOR_RECOMMENDATION]
    )
    selected = recommendation.ranked_options[0]
    for item in recommendation.ranked_options:
        selected_by_rank = response.startswith(str(item.rank))
        selected_by_text = item.option_id in response or item.title in response
        if selected_by_rank or selected_by_text:
            selected = item
            break
    ctx.state[STATE_SELECTED_OPTION_ID] = selected.option_id
    yield Event(route=ROUTE_SELECTED, output=selected.option_id)

def build_replan_input(ctx: Context, node_input: Any) -> str:
    return "\n\n".join(
        [
            "現在のTravelRequest:",
            text(ctx.state.get(STATE_TRAVEL_REQUEST)),
            "現在の推薦:",
            text(ctx.state.get(STATE_COORDINATOR_RECOMMENDATION)),
            "ユーザーの変更希望:",
            text(node_input),
            "条件変更を反映した TravelRequest を作り直してください。",
        ]
    )
def build_replan_input(ctx: Context, node_input: Any) -> str:
    return "\n\n".join(
        [
            "現在のTravelRequest:",
            "条件変更を反映した TravelRequest を作り直してください。",
        ]
    )


def build_planner_input(ctx: Context, node_input: Any) -> str:
    context = build_selected_option_context(ctx, node_input)
    recommendation = context.recommendation
    recommendation_lines = []
    if recommendation is not None:
        cautions = ", ".join(recommendation.cautions) if recommendation.cautions else "なし"
        recommendation_lines = [
            f"- 推薦順位: {recommendation.rank}",
            f"- 推薦理由: {recommendation.reason}",
            f"- 注意点: {cautions}",
        ]

    return "\n\n".join(
        [
            "# Travel request",
            f"- 元の希望: {context.travel_request.raw_user_query}",
            f"- 出発地: {context.travel_request.origin or '要確認'}",
            f"- 期間: {context.travel_request.duration or '要確認'}",
            f"- 予算: {context.travel_request.budget or '要確認'}",
            "# Selected option",
            f"- ID: {context.selected_option.option_id}",
            f"- タイトル: {context.selected_option.title}",
            f"- 目的地: {context.selected_option.destination}",
            f"- コンセプト: {context.selected_option.concept}",
            "# Recommendation notes",
            "\n".join(recommendation_lines) if recommendation_lines else "- 推薦情報: 要確認",
            "# Research report",
            f"- 目的地概要: {context.research_report.destination_summary}",
            f"- アクセス: {context.research_report.access}",
            f"- 概算費用: {context.research_report.estimated_cost}",
            f"- リスク: {', '.join(context.research_report.risks)}",
        ]
    )


def store_itinerary_markdown(ctx: Context, node_input: Any) -> str:
    markdown = text(node_input)
    ctx.state[STATE_ITINERARY_MARKDOWN] = markdown
    return markdown
def build_selected_option_context(ctx: Context, node_input: Any) -> SelectedOptionContext:
    selected_option_id = ctx.state.get(STATE_SELECTED_OPTION_ID) or text(node_input)
    options = [
        TravelOption.model_validate(item)
        for item in ctx.state.get(STATE_TRAVEL_OPTIONS, [])
    ]
    reports = {
        key: ResearchReport.model_validate(value)
        for key, value in ctx.state.get(STATE_RESEARCH_REPORTS, {}).items()
    }
    recommendation = CoordinatorRecommendation.model_validate(
        ctx.state[STATE_COORDINATOR_RECOMMENDATION]
    )
    selected_option = next(option for option in options if option.option_id == selected_option_id)
    selected_recommendation = next(
        (item for item in recommendation.ranked_options if item.option_id == selected_option_id),
        None,
    )
    context = SelectedOptionContext(
        travel_request=TravelRequest.model_validate(ctx.state[STATE_TRAVEL_REQUEST]),
        selected_option=selected_option,
        research_report=reports[selected_option_id],
        evaluations=[],
        recommendation=selected_recommendation,
        coordinator_notes=recommendation.conflict_resolution,
    )
    ctx.state[STATE_SELECTED_OPTION_CONTEXT] = context.model_dump()
    return context