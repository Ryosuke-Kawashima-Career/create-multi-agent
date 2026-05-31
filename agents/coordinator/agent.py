# TODO: Workflow を実装
from __future__ import annotations

from google.adk import Workflow
from google.adk.workflow import DEFAULT_ROUTE

from agents._common import to_a2a_app
from agents.coordinator.clarify import (
    ROUTE_CLARIFY,
    clarify_agent,
    build_reclarify_input,
    capture_user_query,
    request_clarification,
    route_after_clarification,
)


root_agent = Workflow(
    name="dynamic_travel_planning_agent",
    description="Dynamic Research + Multi-Agent Evaluation 型の旅行計画AIエージェント。",
    edges=[
        ("START", capture_user_query, clarify_agent),
        (
            route_after_clarification,
            {
                ROUTE_CLARIFY: request_clarification,
                DEFAULT_ROUTE: candidate_workflow,
            },
        ),
        (request_clarification, build_reclarify_input, clarify_agent),
        (clarify_agent, route_after_clarification),
    ],
)

app = to_a2a_app(root_agent, default_port=8100)

from agents.coordinator.clarify import (
    ROUTE_CLARIFY,
    clarify_agent,
    build_reclarify_input,
    request_clarification,
    route_after_clarification,
)
from agents.coordinator.candidates import (
    store_travel_options,
    strategist_agent,
    travel_research_workflow,
)


candidate_workflow = Workflow(
    name="travel_candidate_workflow",
    description="Creates candidates and researches them.",
    edges=[
        (
            "START",
            strategist_agent,
            store_travel_options,
            travel_research_workflow,
        ),
    ],
)

from agents.coordinator.clarify import (
    ROUTE_CLARIFY,
    clarify_agent,
    build_reclarify_input,
    request_clarification,
    route_after_clarification,
)
from agents.coordinator.candidates import (
    store_travel_options,
    strategist_agent,
    travel_research_workflow,
)


candidate_workflow = Workflow(
    name="travel_candidate_workflow",
    description="Creates candidates and researches them.",
    edges=[
        (
            "START",
            strategist_agent,
            store_travel_options,
            travel_research_workflow,
        ),
    ],
)
