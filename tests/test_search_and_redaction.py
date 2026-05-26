from __future__ import annotations

from hirenest_support.agent_rag import assess_retrieval_coverage, refine_retrieval_query
from hirenest_support.agent_search import search_agent_search
from hirenest_support.incidents import correlate_incidents
from hirenest_support.knowledge import search_knowledge_base
from hirenest_support.redaction import redact_customer_text
from hirenest_support.tickets import search_ticket_history


def test_ticket_search_prioritizes_customer_and_category() -> None:
    tickets = search_ticket_history(
        "Apex Robotics interview invitation email not delivered to all candidates",
        limit=2,
    )

    assert tickets[0]["ticket_id"] == "TCK-4101"
    assert tickets[0]["category"] == "candidate_communication"


def test_knowledge_search_returns_customer_safe_and_internal_refs() -> None:
    refs = search_knowledge_base("interview invitation email delivery all candidates", limit=12)
    paths = {ref["path"] for ref in refs}

    assert "knowledge_base/faq/interview-invitation-email.md" in paths
    assert "knowledge_base/runbooks/messaging-platform-runbook.md" in paths
    assert any(ref["customer_safe"] is False for ref in refs)


def test_incident_correlation_finds_active_invitation_incident() -> None:
    incidents = correlate_incidents("Apex Robotics candidate invitation email delivery delayed")

    assert incidents["likely_related"] is True
    assert incidents["active_matches"][0]["incident_id"] == "INC-2026-0524-INVITE-DELIVERY"


def test_redaction_removes_customer_unsafe_terms() -> None:
    text = "tenant_id: acme-123 has raw logs in the internal timeline from the backend service."

    redacted = redact_customer_text(text)

    assert "acme-123" not in redacted
    assert "raw logs" not in redacted
    assert "backend service" not in redacted


def test_agent_search_without_serving_config_returns_local_fallback(
    monkeypatch,
) -> None:
    monkeypatch.delenv("HIRENEST_AGENT_SEARCH_SERVING_CONFIG", raising=False)

    result = search_agent_search("candidate invitation delivery")

    assert result["backend"] == "local_fallback"
    assert result["configured"] is False


def test_agent_rag_assesses_and_refines_incomplete_ticket_evidence() -> None:
    inquiry = "Apex Robotics interview invitation emails are not delivered to all candidates."
    partial_findings = {"similar_tickets": []}

    assessment = assess_retrieval_coverage(inquiry, "ticket_history", partial_findings)
    refined = refine_retrieval_query(inquiry, "ticket_history", partial_findings)

    assert assessment["sufficient"] is False
    assert "more similar historical tickets" in assessment["missing"]
    assert "candidate invitation email" in refined["query"]
    assert "Messaging Platform" in refined["query"]
