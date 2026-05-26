from __future__ import annotations

from google.adk import Agent

from agents._common import build_a2a_app, model_name
from hirenest_support.discord import send_discord_escalation_message
from hirenest_support.policy import recommend_escalation


def evaluate_escalation_policy(inquiry: str) -> dict:
    """Return severity, SLA, escalation decision, owner team, and customer-safe constraints."""
    return recommend_escalation(inquiry)


def notify_discord_escalation(
    case_summary: str,
    severity: str,
    team: str,
    customer: str = "Unknown",
) -> dict:
    """Send or dry-run an internal Discord escalation notification."""
    return send_discord_escalation_message(case_summary, severity, team, customer)


root_agent = Agent(
    name="escalation_policy_agent",
    model=model_name(),
    description="Applies HireNest severity, escalation, SLA, and communication policies.",
    instruction=(
        "You are the Escalation Policy Agent. "
        "Use evaluate_escalation_policy for every request. Return recommended severity, "
        "reasoning, SLA response deadline, escalation decision, target team, required attachments, "
        "missing information, and customer communication constraints. "
        "If should_escalate is true, use notify_discord_escalation with a concise internal "
        "summary. The Discord tool is safe in local demos because it dry-runs unless credentials "
        "are configured."
    ),
    tools=[evaluate_escalation_policy, notify_discord_escalation],
)

app = build_a2a_app(root_agent, default_port=8105)
