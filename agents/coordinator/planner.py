from __future__ import annotations
from typing import Any
from google.adk.agents.context import Context
from google.adk.events import RequestInput
from google.adk.events.event import Event
from agents.coordinator.planner_models import CoordinatorRecommendation
from agents.coordinator.utils import text
from agents.coordinator.clarify import STATE_TRAVEL_REQUEST
STATE_COORDINATOR_RECOMMENDATION = "coordinator_recommendation"
ROUTE_REPLAN = "replan"
ROUTE_SELECTED = "selected"
MAX_USER_VISIBLE_OPTIONS = 3
STATE_SELECTED_OPTION_ID = "selected_option_id"

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