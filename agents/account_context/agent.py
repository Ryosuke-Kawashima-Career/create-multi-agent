from __future__ import annotations

from google.adk import Agent

from agents._common import build_a2a_app, model_name
from hirenest_support.accounts import get_account_context
from hirenest_support.agent_rag import assess_retrieval_coverage, refine_retrieval_query


def lookup_account_context(inquiry: str) -> dict:
    """Return account, contract, entitlement, contact, health, and SLA context."""
    return get_account_context(inquiry)


def assess_account_context_evidence(inquiry: str, current_findings: dict) -> dict:
    """Assess whether retrieved account evidence is sufficient for the case."""
    return assess_retrieval_coverage(inquiry, "account_context", current_findings)


def refine_account_context_query(inquiry: str, current_findings: dict, attempt: int = 1) -> dict:
    """Return a refined account query when account evidence is incomplete."""
    return refine_retrieval_query(inquiry, "account_context", current_findings, attempt)


root_agent = Agent(
    name="account_context_agent",
    model=model_name(),
    description=(
        "Looks up HireNest customer account, contract, support tier, SLA, "
        "contacts, and health."
    ),
    instruction=(
        "You are the Account Context Agent for HireNest ATS support. "
        "Use an AgentRAG loop: call lookup_account_context, then "
        "assess_account_context_evidence. If it says sufficient=false, call "
        "refine_account_context_query and retry lookup_account_context with the refined query. "
        "Repeat for up to two refinement attempts before finalizing. Return customer name, "
        "plan, support tier, SLA rows, CSM, contacts, entitlements, health score, risk "
        "signals, query attempts, and any remaining missing evidence. "
        "If the customer is unknown, say what identifier is missing."
    ),
    tools=[
        lookup_account_context,
        assess_account_context_evidence,
        refine_account_context_query,
    ],
)

app = build_a2a_app(root_agent, default_port=8103)
