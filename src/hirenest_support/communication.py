from __future__ import annotations

import re
from typing import Any

from hirenest_support.loaders import read_text
from hirenest_support.redaction import redact_customer_text

COMMUNICATION_POLICY_FILES = [
    "policies/customer_communication_policy.md",
    "policies/support_tone_guidelines.md",
    "policies/security_privacy_redaction.md",
]

SENSITIVE_PATTERNS = [
    (re.compile(r"\bINC-\d{4}-[A-Z0-9-]+\b"), "internal incident ID"),
    (re.compile(r"\bTCK-\d+\b"), "internal ticket ID"),
    (re.compile(r"\brunbook\b", re.IGNORECASE), "internal runbook reference"),
    (re.compile(r"\bARR\b|\bcontract value\b", re.IGNORECASE), "account value signal"),
    (re.compile(r"\bhealth score\b", re.IGNORECASE), "account health score"),
    (re.compile(r"\brisk signals?\b", re.IGNORECASE), "internal account risk signal"),
    (re.compile(r"\binternal-only\b|\binternal timeline\b", re.IGNORECASE), "internal-only data"),
    (re.compile(r"\braw logs?\b|\bstack traces?\b|\btraces?\b", re.IGNORECASE), "raw diagnostics"),
    (re.compile(r"\btenant[_ -]?id\b|\bqueue[_ -]?id\b", re.IGNORECASE), "internal identifier"),
    (
        re.compile(r"\binternal_summary\b|\bengineering hypothesis\b", re.IGNORECASE),
        "internal hypothesis",
    ),
]

BLOCKED_RESPONSE_PATTERNS = [
    (re.compile(r"\bINC-\d{4}-[A-Z0-9-]+\b"), "incident ID"),
    (re.compile(r"\bTCK-\d+\b"), "ticket ID"),
    (re.compile(r"\bARR\b|\$\d[\d,]*(?:\.\d+)?"), "account value"),
    (re.compile(r"\bhealth score\b", re.IGNORECASE), "health score"),
    (re.compile(r"\brunbook\b", re.IGNORECASE), "runbook"),
    (re.compile(r"\braw logs?\b|\bstack traces?\b", re.IGNORECASE), "raw diagnostics"),
    (re.compile(r"\btenant[_ -]?id\b|\bqueue[_ -]?id\b", re.IGNORECASE), "internal identifier"),
]


def generate_customer_response_package(support_brief: str) -> dict[str, Any]:
    """Generate a customer-facing response package from an already-prepared support brief."""
    policy_context = load_communication_policy_context()
    case = _extract_case_context(support_brief)
    risks = _find_disclosure_risks(support_brief)

    subject = _subject(case)
    customer_response = _customer_response(case)
    blocked_terms = _blocked_response_terms(f"{subject}\n{customer_response}")
    review_reasons = _human_review_reasons(case, risks, blocked_terms)

    return {
        "subject": subject,
        "customer_response": customer_response,
        "summary_for_agent": _summary_for_agent(case),
        "disclosure_check": {
            "safe_to_send": not blocked_terms,
            "policy_files_used": list(policy_context),
            "omitted_or_softened": bool(risks),
            "omitted_items": risks,
            "blocked_terms_in_response": blocked_terms,
        },
        "assumptions": _assumptions(case),
        "requires_human_review": bool(review_reasons),
        "human_review_reason": review_reasons,
    }


def load_communication_policy_context() -> dict[str, str]:
    """Load only customer-communication policy files used by this agent."""
    return {path: read_text(path) for path in COMMUNICATION_POLICY_FILES}


def _extract_case_context(brief: str) -> dict[str, Any]:
    lowered = brief.lower()
    severity = _match(brief, r"Recommended severity:\s*(SEV\d)", "Unknown")
    category = _match(brief, r"Problem category:\s*([^\n]+)", "support case").strip()
    support_tier = _match(brief, r"Support tier:\s*([^\n]+)", "Unknown").strip()
    impact = _match(brief, r"Impact scope:\s*([^\n]+)", "the reported issue").strip()
    update_frequency = _match(brief, r"SLA update frequency:\s*([^\n]+)", "").strip()
    status_update = _match(brief, r"Customer-shareable status update:\s*([^\n]+)", "").strip()
    if status_update.lower().startswith("no public"):
        status_update = ""

    return {
        "customer_name": _match(brief, r"Customer name:\s*([^\n]+)", "").strip(),
        "severity": severity,
        "category": category,
        "support_tier": support_tier,
        "impact": impact,
        "next_update": update_frequency,
        "questions": _split_csv(
            _match(brief, r"Additional information needed:\s*([^\n]+)", "").strip()
        ),
        "incident_related": "related active incident: none found" not in lowered
        and "related active incident:" in lowered,
        "status_update": status_update,
        "confirmed_cause": _confirmed_customer_facing_cause(brief),
        "has_uncertainty": _has_uncertainty(brief),
        "broad_impact": _has_broad_impact(brief),
        "enterprise_or_premier": support_tier.lower() == "premier"
        or "enterprise" in lowered
        or "premier" in lowered,
    }


def _customer_response(case: dict[str, Any]) -> str:
    lines = ["Hello,", ""]
    impact = _sentence_fragment(case["impact"])
    if case["enterprise_or_premier"] or case["severity"] in {"SEV1", "SEV2"}:
        lines.append(
            f"We understand the reported business impact: {impact}. "
            "We are treating this with urgency."
        )
    else:
        lines.append(f"Thank you for reporting this. We understand the impact as: {impact}.")

    lines.append(_investigation_sentence(case))

    if case["confirmed_cause"]:
        lines.append(f"The confirmed cause is {case['confirmed_cause']}.")

    next_steps = _next_steps(case)
    if next_steps:
        lines.append(f"Next steps: {next_steps}")

    questions = case["questions"]
    if questions:
        lines.append(
            f"Please share the following details: {', '.join(questions)}. "
            "This will help us continue the investigation."
        )

    if case["next_update"]:
        lines.append(f"We will provide the next update within {case['next_update']}.")

    return _sanitize_customer_text("\n".join(lines).strip())


def _investigation_sentence(case: dict[str, Any]) -> str:
    category = case["category"].lower()
    if case["incident_related"]:
        return "We are checking whether this may be related to a known service issue."
    if "candidate_communication" in category:
        return "We are checking invitation delivery, message rendering, and recipient status."
    if "calendar_integration" in category:
        return "We are checking calendar availability, connection state, and scheduling settings."
    if "careers_site" in category:
        return "We are checking the published job page and application form behavior."
    if "scorecard_permissions" in category:
        return "We are checking interview-stage access and evaluation form permissions."
    if "candidate_import" in category:
        return "We are reviewing the import job, field mappings, and skipped-row details."
    return "We are checking the reported behavior and related service health."


def _next_steps(case: dict[str, Any]) -> str:
    category = case["category"].lower()
    if case["incident_related"]:
        return (
            "validate the current service status, confirm whether your case is affected, "
            "and share any available mitigation."
        )
    if "candidate_communication" in category:
        return "review delivery timing, template rendering, and resend options."
    if "calendar_integration" in category:
        return "review calendar connection state, free/busy access, and interviewer settings."
    if "careers_site" in category:
        return "review the published form, job visibility, and recent page changes."
    if "scorecard_permissions" in category:
        return "review the hiring team role, interview stage, and scorecard template sharing."
    if "candidate_import" in category:
        return "compare the import preview, skipped rows, and field mappings."
    return "review the case details and confirm the best path to resolution."


def _subject(case: dict[str, Any]) -> str:
    category = case["category"].lower()
    if "candidate_communication" in category:
        return "Update on interview invitation delivery"
    if "calendar_integration" in category:
        return "Update on calendar availability"
    if "careers_site" in category:
        return "Update on job application form issue"
    if "scorecard_permissions" in category:
        return "Update on scorecard access"
    if "candidate_import" in category:
        return "Update on candidate import review"
    return "Update on your HireNest support case"


def _summary_for_agent(case: dict[str, Any]) -> str:
    parts = [
        f"{case['severity']} {case['category']} response",
        f"support tier: {case['support_tier']}",
        f"incident-related: {case['incident_related']}",
    ]
    if case["next_update"]:
        parts.append(f"next update: {case['next_update']}")
    return "; ".join(parts)


def _assumptions(case: dict[str, Any]) -> list[str]:
    assumptions = [
        "The coordinator-provided brief contains the approved facts for customer communication."
    ]
    if not case["confirmed_cause"]:
        assumptions.append("Root cause is not confirmed as customer-facing, so no cause is stated.")
    return assumptions


def _human_review_reasons(
    case: dict[str, Any], risks: list[str], blocked_terms: list[str]
) -> list[str]:
    reasons: list[str] = []
    severity = case["severity"]
    category = case["category"].lower()
    impact = case["impact"].lower()

    if severity in {"SEV1", "SEV2"}:
        reasons.append(f"{severity} case")
    if any(
        signal in category or signal in impact
        for signal in [
            "candidate data",
            "security",
            "privacy",
            "candidate_communication",
            "calendar_integration",
            "careers_site",
            "candidate_import",
            "data loss",
            "availability",
            "outage",
        ]
    ):
        reasons.append("sensitive issue category or impact")
    if case["incident_related"]:
        reasons.append("response mentions a possible known issue or service incident")
    if case["broad_impact"] or case["enterprise_or_premier"]:
        reasons.append("broad impact or enterprise/Premier customer")
    if case["has_uncertainty"]:
        reasons.append("input contains uncertainty about cause, scope, or workaround")
    if risks:
        reasons.append("internal or sensitive details were omitted or softened")
    if blocked_terms:
        reasons.append("customer response still contains blocked disclosure terms")

    return _dedupe(reasons)


def _find_disclosure_risks(text: str) -> list[str]:
    risks: list[str] = []
    for pattern, label in SENSITIVE_PATTERNS:
        if pattern.search(text):
            risks.append(label)
    return _dedupe(risks)


def _blocked_response_terms(text: str) -> list[str]:
    blocked: list[str] = []
    for pattern, label in BLOCKED_RESPONSE_PATTERNS:
        if pattern.search(text):
            blocked.append(label)
    return _dedupe(blocked)


def _sanitize_sentence(text: str) -> str:
    result = redact_customer_text(text)
    result = re.sub(r"\bINC-\d{4}-[A-Z0-9-]+\b", "the service issue", result)
    result = re.sub(r"\bTCK-\d+\b", "the prior support case", result)
    result = re.sub(r"\s+", " ", result)
    return result.replace(". ", ".\n").replace("? ", "?\n")


def _sanitize_customer_text(text: str) -> str:
    return "\n".join(_sanitize_inline(line) for line in text.splitlines())


def _sanitize_inline(text: str) -> str:
    result = redact_customer_text(text)
    result = re.sub(r"\bINC-\d{4}-[A-Z0-9-]+\b", "the service issue", result)
    result = re.sub(r"\bTCK-\d+\b", "the prior support case", result)
    return re.sub(r"\s+", " ", result).strip()


def _sentence_fragment(text: str) -> str:
    return text.strip().rstrip(".:;")


def _confirmed_customer_facing_cause(brief: str) -> str:
    cause = _match(
        brief,
        r"Customer-facing confirmed (?:root )?cause:\s*([^\n]+)",
        "",
    ).strip()
    return _sanitize_inline(cause).strip(".") if cause else ""


def _has_uncertainty(brief: str) -> bool:
    return bool(
        re.search(
            r"\b(uncertain|unknown|possible|possibly|may|might|checking whether|investigating|"
            r"customer-specific|workaround|validate|confirm)\b",
            brief,
            re.IGNORECASE,
        )
    )


def _has_broad_impact(brief: str) -> bool:
    return bool(
        re.search(
            r"\b(all users|all employees|many users|entire team|company-wide|broad|"
            r"all customers|all candidates|all jobs|many candidates|candidate-facing)\b",
            brief,
            re.IGNORECASE,
        )
    )


def _match(text: str, pattern: str, default: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default


def _split_csv(text: str) -> list[str]:
    if not text:
        return []
    return [item.strip() for item in text.split(",") if item.strip() and item.strip() != "Unknown"]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
