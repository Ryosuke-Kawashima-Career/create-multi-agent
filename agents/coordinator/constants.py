from __future__ import annotations

ROUTE_RETRY = "retry"

INVESTIGATION_AGENT_NAMES = (
    "account_context_agent",
    "ticket_history_agent",
    "incident_status_agent",
    "knowledge_base_agent",
    "diagnostics_agent",
)

STATE_SYNTHESIS_BRIEF = "temp:synthesis_brief"
STATE_ESCALATION_POLICY = "temp:escalation_policy"
STATE_INVESTIGATION_PLAN = "temp:investigation_plan"
STATE_CLARIFICATION_QUESTIONS = "temp:clarification_questions"
STATE_CLARIFICATION_REQUEST = "temp:clarification_request"
