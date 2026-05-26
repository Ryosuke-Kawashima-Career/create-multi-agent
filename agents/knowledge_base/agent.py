from __future__ import annotations

from google.adk import Agent

from agents._common import build_a2a_app, model_name
from hirenest_support.agent_rag import assess_retrieval_coverage, refine_retrieval_query
from hirenest_support.agent_search import search_agent_search
from hirenest_support.knowledge import search_knowledge_base


def search_relevant_knowledge(inquiry: str) -> dict:
    """Search FAQ, troubleshooting, runbook, policy, release note, and known-issue docs."""
    return {"references": search_knowledge_base(inquiry)}


def search_hirenest_agent_search(inquiry: str) -> dict:
    """Search the configured Gemini Enterprise Agent Search corpus."""
    return search_agent_search(inquiry)


def assess_knowledge_evidence(inquiry: str, current_findings: dict) -> dict:
    """Assess whether retrieved knowledge references are sufficient for the case."""
    return assess_retrieval_coverage(inquiry, "knowledge_base", current_findings)


def refine_knowledge_query(inquiry: str, current_findings: dict, attempt: int = 1) -> dict:
    """Return a refined knowledge-base query when retrieved evidence is incomplete."""
    return refine_retrieval_query(inquiry, "knowledge_base", current_findings, attempt)


root_agent = Agent(
    name="knowledge_base_agent",
    model=model_name(),
    description="Searches HireNest FAQ, troubleshooting, runbooks, policy, and product docs.",
    instruction=(
        "You are the Knowledge Base Agent for HireNest ATS support. "
        "Use an AgentRAG loop: search_hirenest_agent_search and search_relevant_knowledge, "
        "then call assess_knowledge_evidence. If it says sufficient=false, call "
        "refine_knowledge_query and search again with the refined query. Repeat for up to two "
        "refinement attempts before finalizing. Separate customer-safe references from "
        "internal-only runbook and policy references. Include troubleshooting steps, "
        "workarounds, internal checks, query attempts, and any remaining missing evidence."
    ),
    tools=[
        search_hirenest_agent_search,
        search_relevant_knowledge,
        assess_knowledge_evidence,
        refine_knowledge_query,
    ],
)

app = build_a2a_app(root_agent, default_port=8102)
