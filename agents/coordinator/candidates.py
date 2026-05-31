from __future__ import annotations

import asyncio
from typing import Any

from google.adk import Agent, Context
from google.adk.tools import google_search
from google.adk.workflow import node

from agents.coordinator.candidates_models import ResearchReport, TravelOption, TravelOptions
from agents.coordinator.clarify import STATE_TRAVEL_REQUEST
from agents.coordinator.utils import dump, text

STATE_TRAVEL_OPTIONS = "travel_options"
STATE_RESEARCH_REPORTS = "research_reports"

STRATEGIST_AGENT_MODEL = "gemini-3.5-flash"
RESEARCH_AGENT_MODEL = "gemini-3.1-flash-lite"
RESEARCH_REPORT_FORMATTER_MODEL = "gemini-3.1-flash-lite"

strategist_agent = Agent(
    name="strategist",
    model=STRATEGIST_AGENT_MODEL,
    description="旅行方針と候補地を6案作る。",
    output_schema=TravelOptions,
    instruction=(
        "TravelRequest をもとに、旅行候補を6案作ってください。"
        "詳細旅程ではなく、旅行方針、候補地、調査観点を作ります。"
        "option_id は option_1, option_2 のように安定した値にしてください。"
    ),
    mode="single_turn",
)

research_agent = Agent(
    name="research_agent",
    model=RESEARCH_AGENT_MODEL,
    description="候補ごとの旅行リサーチを行う。",
    tools=[google_search],
    instruction=(
        "あなたは旅行リサーチ担当です。入力に含まれる TravelOption について、"
        "google_search を使ってアクセス、費用感、宿泊エリア、観光地、食事、"
        "リスク、季節性を調べてください。"
        "option_id は入力の値を必ず維持します。"
        "source_notes に相当する確認元名や根拠メモも自然文で含めてください。"
        "重要: google_search と structured output は同時に使えないため、"
        "あなたは構造化JSONではなく調査メモを返します。"
    ),
    mode="single_turn",
)

research_report_formatter = Agent(
    name="research_report_formatter",
    model=RESEARCH_REPORT_FORMATTER_MODEL,
    description="検索済みリサーチメモをResearchReportへ構造化する。",
    output_schema=ResearchReport,
    instruction=(
        "入力には TravelRequest、TravelOption、google_search 済みの調査メモが含まれます。"
        "調査メモを ResearchReport に構造化してください。"
        "新しい事実を追加で断定せず、不明な項目は「要確認」と書いてください。"
        "option_id は TravelOption の値を必ず維持してください。"
    ),
    mode="single_turn",
)

def store_travel_options(ctx: Context, node_input: TravelOptions) -> TravelOptions:
    ctx.state[STATE_TRAVEL_OPTIONS] = [option.model_dump() for option in node_input.options]
    return node_input


@node(name="research_candidate", rerun_on_resume=True)
async def research_candidate(ctx: Context, node_input: dict[str, Any]) -> ResearchReport:
    request = ctx.state.get(STATE_TRAVEL_REQUEST, {})
    research_memo = await ctx.run_node(research_agent, build_research_input(request, node_input))
    return await ctx.run_node(
        research_report_formatter,
        build_research_report_input(request, node_input, research_memo),
    )


@node(name="travel_research_workflow", rerun_on_resume=True)
async def travel_research_workflow(ctx: Context, node_input: Any) -> dict[str, dict[str, Any]]:
    options = ctx.state.get(STATE_TRAVEL_OPTIONS)
    if not options and isinstance(node_input, TravelOptions):
        options = [option.model_dump() for option in node_input.options]
        ctx.state[STATE_TRAVEL_OPTIONS] = options

    tasks = [ctx.run_node(research_candidate, option) for option in options or []]
    reports = await asyncio.gather(*tasks)
    return collect_research_reports(ctx, reports)


def collect_research_reports(ctx: Context, node_input: Any) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    values = node_input.values() if isinstance(node_input, dict) else node_input
    for value in values or []:
        data = dump(value)
        if isinstance(data, dict) and data.get("option_id"):
            reports[data["option_id"]] = data
    ctx.state[STATE_RESEARCH_REPORTS] = reports
    return reports
