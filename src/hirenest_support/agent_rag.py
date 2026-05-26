from __future__ import annotations

from typing import Any

from hirenest_support.intake import parse_case
from hirenest_support.text import tokens

DOMAIN_REQUIREMENTS = {
    "ticket_history": [
        "at least three similar tickets",
        "same category evidence",
        "same customer or same workflow evidence",
        "cause and resolution evidence",
    ],
    "knowledge_base": [
        "customer-safe reference",
        "internal runbook or policy reference",
        "known issue or release-note context",
    ],
    "incident_status": [
        "active incident check",
        "historical incident comparison",
        "customer-shareable status update when incident-related",
    ],
    "account_context": [
        "customer account match",
        "contract and support tier",
        "SLA rows",
        "entitlements and contacts",
    ],
}

CATEGORY_EXPANSIONS = {
    "candidate_communication": [
        "candidate invitation email delivery suppression template sender domain",
        "Messaging Platform",
    ],
    "calendar_integration": [
        "Google Calendar free busy availability OAuth scope interviewer scheduling",
        "Scheduling Integrations",
    ],
    "careers_site": [
        "careers site public job page application form custom question CDN cache",
        "Careers Site Platform",
    ],
    "scorecard_permissions": [
        "scorecard evaluation permission interviewer role hiring team stage template",
        "Permissions and Workflow",
    ],
    "candidate_import": [
        "CSV import candidate data field mapping skipped rows dedupe preview",
        "Data Import Operations",
    ],
    "reporting": ["recruiting analytics dashboard pipeline metrics reporting"],
}


def assess_retrieval_coverage(
    inquiry: str,
    domain: str,
    findings: Any,
) -> dict[str, Any]:
    """Assess whether a specialist has enough retrieved evidence to answer responsibly."""
    intake = parse_case(inquiry)
    text = _flatten_text(findings)
    result_count = _count_results(findings)
    missing: list[str] = []

    if domain == "ticket_history":
        if result_count < 3:
            missing.append("more similar historical tickets")
        if intake.category and intake.category not in text:
            missing.append(f"same-category examples for {intake.category}")
        if intake.customer_id and intake.customer_id.lower() not in text:
            missing.append(f"same-customer examples for {intake.customer_name}")
        if "cause" not in text or "resolution" not in text:
            missing.append("past cause and resolution details")
    elif domain == "knowledge_base":
        if result_count < 4:
            missing.append("more knowledge references")
        if "customer_safe" not in text and "customer-safe" not in text:
            missing.append("customer-safe troubleshooting reference")
        if "runbook" not in text and "policy" not in text:
            missing.append("internal runbook or policy reference")
        if "known" not in text and "release" not in text:
            missing.append("known issue or release-note context")
    elif domain == "incident_status":
        if "active_matches" not in text and "incident_id" not in text:
            missing.append("active incident correlation")
        if "historical_matches" not in text and "historical" not in text:
            missing.append("historical incident comparison")
        if "status_updates" not in text and "message" not in text:
            missing.append("customer-shareable status update")
    elif domain == "account_context":
        if "found" in text and "false" in text:
            missing.append("customer name or customer_id")
        for required in ["contract", "support_tier", "sla", "entitlements", "contacts"]:
            if required not in text:
                missing.append(required)
    else:
        missing.extend(DOMAIN_REQUIREMENTS.get(domain, []))

    if _has_category_terms(intake.category, text):
        missing = [item for item in missing if not item.startswith("same-category")]

    return {
        "domain": domain,
        "sufficient": not missing,
        "missing": missing,
        "result_count": result_count,
        "detected_category": intake.category,
        "detected_customer": intake.customer_name,
        "reasoning": _reasoning(domain, missing, result_count),
    }


def refine_retrieval_query(
    inquiry: str,
    domain: str,
    findings: Any,
    attempt: int = 1,
) -> dict[str, Any]:
    """Create a narrower follow-up query from missing evidence and detected case signals."""
    assessment = assess_retrieval_coverage(inquiry, domain, findings)
    intake = parse_case(inquiry)
    parts = [inquiry.strip()]
    if intake.customer_name:
        parts.append(intake.customer_name)
    parts.append(intake.category)
    parts.extend(intake.key_signals)
    parts.extend(CATEGORY_EXPANSIONS.get(intake.category, []))
    parts.extend(assessment["missing"])
    if attempt >= 2:
        parts.append("include lower-ranked adjacent cases and internal references")

    refined = " ".join(part for part in parts if part)
    return {
        "query": refined,
        "attempt": attempt,
        "domain": domain,
        "based_on_missing": assessment["missing"],
    }


def _flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, dict):
        return " ".join(f"{key} {_flatten_text(item)}" for key, item in value.items()).lower()
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value).lower()
    return str(value).lower()


def _count_results(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if not isinstance(value, dict):
        return 0
    for key in [
        "similar_tickets",
        "references",
        "results",
        "active_matches",
        "historical_matches",
        "contacts",
        "entitlements",
    ]:
        item = value.get(key)
        if isinstance(item, list) and item:
            return len(item)
    if value.get("found") is True:
        return 1
    return 0


def _has_category_terms(category: str, text: str) -> bool:
    expanded = " ".join(CATEGORY_EXPANSIONS.get(category, []))
    return bool(tokens(category) & tokens(text)) or bool(tokens(expanded) & tokens(text))


def _reasoning(domain: str, missing: list[str], result_count: int) -> str:
    required = "; ".join(DOMAIN_REQUIREMENTS.get(domain, []))
    if not missing:
        return f"Retrieved evidence satisfies {domain} requirements: {required}."
    return (
        f"Retrieved {result_count} result(s), but {domain} still lacks: "
        f"{', '.join(missing)}."
    )
