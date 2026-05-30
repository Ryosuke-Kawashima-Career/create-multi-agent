from __future__ import annotations

import os

from google.adk import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

COMFORT_AGENT_MODEL = "gemini-3.5-flash"

root_agent = Agent(
    name="comfort_agent",
    model=COMFORT_AGENT_MODEL,
    description="旅行候補を移動負荷、休憩、宿泊快適性、疲労しにくさで評価する。",
    instruction=(
        "あなたは comfort_agent です。初回評価では EvaluationReport を返してください。"
        "候補ごとの評価は option_evaluations に option_id, score, "
        "comment, concerns を入れてください。"
        "移動負荷、休憩しやすさ、宿泊快適性、疲労しにくさを重視します。"
        "Revision を求められた場合は RevisionReport を返し、修正不要なら revision_note に "
        "'no change' と明記してください。revised_report も option_evaluations 形式です。"
    ),
    mode="chat",
)

app = to_a2a(
    root_agent,
    host=os.getenv("A2A_HOST", "localhost"),
    port=int(os.getenv("PORT", "8101")),
    protocol=os.getenv("A2A_PROTOCOL", "http"),
)
