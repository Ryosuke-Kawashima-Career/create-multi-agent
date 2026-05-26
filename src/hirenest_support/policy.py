from __future__ import annotations

from typing import Any

from hirenest_support.accounts import get_account_context, get_sla_for
from hirenest_support.incidents import correlate_incidents
from hirenest_support.intake import parse_case


def recommend_escalation(query: str) -> dict[str, Any]:
    intake = parse_case(query)
    account = get_account_context(query)
    incidents = correlate_incidents(query, limit=2)
    support_tier = account.get("contract", {}).get("support_tier", "Unknown")
    severity = _severity(query, intake.category, support_tier, incidents["likely_related"])
    team = _team(intake.category, query)
    should_escalate = severity in {"SEV1", "SEV2"} or intake.category == "candidate_import"
    sla = get_sla_for(query, severity)

    return {
        "severity": severity,
        "severity_reason": _severity_reason(
            intake.category, support_tier, incidents["likely_related"], query
        ),
        "sla": sla,
        "should_escalate": should_escalate,
        "team": team if should_escalate else "Support owns initial response",
        "reason": _escalation_reason(intake.category, severity, incidents["likely_related"]),
        "attach": _attachments(intake.category),
        "additional_info_needed": _additional_info_needed(intake.category),
        "customer_safe_constraints": [
            "Do not include raw logs, tenant IDs, backend queue names, or internal timelines.",
            "Avoid definitive root-cause statements until the owner team confirms the finding.",
        ],
    }


def _severity(query: str, category: str, support_tier: str, likely_incident: bool) -> str:
    lowered = query.lower()
    if category == "careers_site" and (
        "all jobs" in lowered or "application form" in lowered or "全求人" in lowered
    ):
        return "SEV2"
    if category == "candidate_communication" and (
        "all candidates" in lowered or "business impact" in lowered or "業務影響" in lowered
    ):
        return "SEV2" if support_tier == "Premier" or likely_incident else "SEV3"
    if category == "calendar_integration" and ("blocked" in lowered or "業務影響" in lowered):
        return "SEV2" if support_tier == "Premier" or likely_incident else "SEV3"
    if category == "candidate_import":
        return "SEV3"
    if likely_incident:
        return "SEV2"
    return "SEV3"


def _team(category: str, query: str) -> str:
    lowered = query.lower()
    if category == "candidate_communication":
        return "Messaging Platform"
    if category == "calendar_integration" or "google calendar" in lowered:
        return "Scheduling Integrations"
    if category == "careers_site":
        return "Careers Site Platform"
    if category == "scorecard_permissions":
        return "Permissions and Workflow"
    if category == "candidate_import":
        return "Data Import Operations"
    if category == "reporting":
        return "Recruiting Analytics"
    return "Support Engineering"


def _severity_reason(category: str, support_tier: str, likely_incident: bool, query: str) -> str:
    if category == "candidate_communication":
        return f"{support_tier} customer reports candidate-facing invitation delivery impact."
    if category == "calendar_integration":
        incident_text = " with active incident correlation" if likely_incident else ""
        return f"Interview scheduling availability affects recruiting workflow{incident_text}."
    if category == "careers_site":
        return "Candidate application submission is affected on published job pages."
    if category == "candidate_import":
        return (
            "Candidate data import quality affects recruiting operations "
            "but no outage is reported."
        )
    return "Severity is based on reported customer impact and current incident correlation."


def _escalation_reason(category: str, severity: str, likely_incident: bool) -> str:
    if category == "candidate_import":
        return (
            "Data Import Operations should validate CSV mappings, skipped rows, "
            "and recovery options."
        )
    if likely_incident:
        return (
            f"{severity} case may be tied to an active incident and needs "
            "owner-team confirmation."
        )
    return f"{severity} impact meets the escalation policy threshold."


def _attachments(category: str) -> list[str]:
    if category == "candidate_communication":
        return [
            "Affected candidate count",
            "Example candidate IDs",
            "Invitation template ID",
            "Sender mailbox",
            "Relevant historical ticket IDs",
        ]
    if category == "calendar_integration":
        return [
            "Affected interviewer emails",
            "Google Calendar reconnect timestamp",
            "Free/busy visibility settings",
            "Example scheduling link or requisition ID",
        ]
    if category == "careers_site":
        return [
            "Published job IDs",
            "Careers site URL",
            "Screenshot or console error",
            "Recent page template changes",
        ]
    if category == "scorecard_permissions":
        return ["Requisition ID", "Interview stage", "Interviewer role", "Scorecard template ID"]
    if category == "candidate_import":
        return ["Import job ID", "CSV headers", "Sanitized sample rows", "Dedupe mode"]
    return ["Customer impact summary", "Timeline", "Relevant logs or screenshots"]


def _additional_info_needed(category: str) -> list[str]:
    if category == "candidate_communication":
        return [
            "Exact first failure time",
            "Example candidate IDs",
            "Whether manual resend works",
        ]
    if category == "calendar_integration":
        return ["Affected interviewers", "Calendar reconnect time", "Free/busy visibility"]
    if category == "careers_site":
        return ["Job posting URLs", "Browser details", "Recent template changes"]
    if category == "candidate_import":
        return ["Import job ID", "Expected candidate count", "Sanitized sample missing rows"]
    return ["Affected users", "First observed time", "Screenshots or error messages"]
