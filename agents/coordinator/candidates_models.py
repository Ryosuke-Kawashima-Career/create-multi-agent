from __future__ import annotations

from pydantic import BaseModel, Field


class TravelOption(BaseModel):
    option_id: str = Field(description="候補を一意に識別するID。例: option_1。")
    title: str = Field(description="ユーザーに見せられる短い候補名。")
    destination: str = Field(description="主な目的地またはエリア。")
    concept: str = Field(description="旅行方針。")
    research_focus: list[str] = Field(description="調査で確認すべき観点。")
    fit_hypothesis: str = Field(description="この候補が合いそうな理由の仮説。")


class TravelOptions(BaseModel):
    options: list[TravelOption] = Field(min_length=3, max_length=5)


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
