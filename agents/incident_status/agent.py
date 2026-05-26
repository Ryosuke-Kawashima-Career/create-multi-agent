from __future__ import annotations

from google.adk import Agent

from agents._common import build_a2a_app, model_name
from hirenest_support.agent_rag import assess_retrieval_coverage, refine_retrieval_query
from hirenest_support.incidents import correlate_incidents, get_incident_timeline


def check_incident_status(inquiry: str) -> dict:
    """Correlate the inquiry with active and historical HireNest incidents."""
    return correlate_incidents(inquiry)


def retrieve_incident_timeline(incident_id: str) -> dict:
    """Retrieve the internal timeline for a known incident ID."""
    return get_incident_timeline(incident_id)


def assess_incident_evidence(inquiry: str, current_findings: dict) -> dict:
    """Assess whether retrieved incident evidence is sufficient for the case."""
    return assess_retrieval_coverage(inquiry, "incident_status", current_findings)


def refine_incident_query(inquiry: str, current_findings: dict, attempt: int = 1) -> dict:
    """Return a refined incident query when retrieved evidence is incomplete."""
    return refine_retrieval_query(inquiry, "incident_status", current_findings, attempt)


root_agent = Agent(
    name="incident_status_agent",
    model=model_name(),
    description="Checks active and historical incidents and public status updates.",
    instruction=(
        "You are the Incident Status Agent. "
        "Use an AgentRAG loop: call check_incident_status, then assess_incident_evidence. "
        "If it says sufficient=false, call refine_incident_query and check again with the "
        "refined query. Repeat for up to two refinement attempts before finalizing. If active "
        "or highly relevant historical incidents are returned, use retrieve_incident_timeline "
        "for the top incident before summarizing. Return active incident correlation, "
        "historical incident similarities, known-vs-customer-specific assessment, "
        "customer-shareable status updates, query attempts, and remaining missing evidence. "
        "Do not expose internal incident timeline details in customer-safe text."
    ),
    tools=[
        check_incident_status,
        retrieve_incident_timeline,
        assess_incident_evidence,
        refine_incident_query,
    ],
)

app = build_a2a_app(root_agent, default_port=8104)
