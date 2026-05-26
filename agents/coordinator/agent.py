from __future__ import annotations

from google.adk import Workflow

from agents._common import build_a2a_app

support_resolution_workflow = Workflow(
    name="support_case_resolution_workflow",
    description="Runs parallel investigation through final package generation.",
    edges=[],  # TODO
)

root_agent = Workflow(
    name="support_coordinator_agent",
    description="Runs the generic Support Case Resolution Workflow over specialist A2A agents.",
    edges=[],  # TODO
)

app = build_a2a_app(root_agent, default_port=8100)
