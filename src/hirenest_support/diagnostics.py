from __future__ import annotations

from typing import Any

from hirenest_support.intake import parse_case


def recommend_diagnostics(inquiry: str) -> dict[str, Any]:
    intake = parse_case(inquiry)
    return {
        "category": intake.category,
        "impact_scope": intake.impact_scope,
        "initial_urgency": intake.initial_urgency,
        "diagnostic_focus": _diagnostic_focus(intake.category),
        "evidence_to_collect": _evidence_to_collect(intake.category),
        "clarification_questions": _clarification_questions(inquiry, intake.category),
        "customer_safe_next_steps": _customer_safe_next_steps(intake.category),
    }


def _diagnostic_focus(category: str) -> list[str]:
    if category == "candidate_communication":
        return [
            "Compare candidate invitation events, mail provider responses, and suppression state.",
            "Check whether the invitation template renders required tokens and sender identity.",
            "Separate one-candidate deliverability from broad candidate-facing delivery impact.",
        ]
    if category == "calendar_integration":
        return [
            "Check Google Calendar OAuth scopes, free/busy visibility, and token freshness.",
            "Compare interviewer working hours, time zone, and room/resource calendar settings.",
        ]
    if category == "careers_site":
        return [
            "Confirm job posting publication state, custom domain cache, and form embed version.",
            "Check console errors and whether required custom fields hide the form.",
        ]
    if category == "scorecard_permissions":
        return [
            "Compare interviewer role, hiring-team membership, and interview-stage assignment.",
            "Check scorecard template sharing and whether confidential fields are restricted.",
        ]
    if category == "candidate_import":
        return [
            "Validate CSV headers, field mappings, required columns, and dedupe behavior.",
            "Compare import preview counts with created, skipped, and failed candidate rows.",
        ]
    if category == "reporting":
        return [
            "Compare affected analytics dashboards, filters, regions, and time windows.",
            "Check whether pipeline metrics lag behind candidate event ingestion.",
        ]
    return [
        "Classify the affected workflow and collect first-failure timing.",
        "Confirm customer, impact scope, and visible error or symptom.",
    ]


def _evidence_to_collect(category: str) -> list[str]:
    if category == "candidate_communication":
        return [
            "Example candidate IDs",
            "Interview invitation sent timestamps",
            "Recipient domains and bounce or suppression status",
            "Template ID and sender mailbox",
            "Whether manual resend works",
        ]
    if category == "calendar_integration":
        return [
            "Affected interviewer email addresses",
            "Calendar provider and OAuth reconnect time",
            "Free/busy visibility setting",
            "Working hours and time zone",
            "Example scheduling link or requisition ID",
        ]
    if category == "careers_site":
        return [
            "Job posting IDs",
            "Careers site URL and custom domain",
            "Browser and device details",
            "Screenshot or console error",
            "Recent page template or custom field changes",
        ]
    if category == "scorecard_permissions":
        return [
            "Interview stage and requisition ID",
            "Affected interviewer roles",
            "Scorecard template ID",
            "Expected versus actual field visibility",
        ]
    if category == "candidate_import":
        return [
            "CSV file name and import job ID",
            "Expected and actual candidate counts",
            "Missing field names",
            "Sample sanitized rows",
            "Dedupe mode and field mapping",
        ]
    return ["Affected workflow", "First observed time", "Screenshots or error messages"]


def _clarification_questions(inquiry: str, category: str) -> list[str]:
    lowered = inquiry.lower()
    questions: list[str] = []
    known_customers = ["apex", "bluewave", "clearpath", "deltahire", "evergreen"]
    if not any(word in lowered for word in known_customers):
        questions.append("Which customer or tenant is affected?")
    if category == "candidate_communication" and not any(
        word in lowered for word in ["all candidates", "all jobs", "全候補者"]
    ):
        questions.append("Are all candidates affected, or only a subset of invitations?")
    if category == "calendar_integration" and "interviewer" not in lowered:
        questions.append("Which interviewers or calendar resources show no availability?")
    if category == "candidate_import" and "job" not in lowered:
        questions.append("Which import job ID or CSV file should be reviewed?")
    if not any(word in lowered for word in ["since", "yesterday", "today", "時", "first"]):
        questions.append("When did the issue first start?")
    return questions


def _customer_safe_next_steps(category: str) -> list[str]:
    if category == "candidate_communication":
        return [
            "Ask for example candidate IDs and sent timestamps.",
            "Confirm whether manual resend succeeds before stating a delivery cause.",
        ]
    if category == "calendar_integration":
        return [
            "Ask for affected interviewer calendars and recent reconnect attempts.",
            "Confirm Google Calendar free/busy settings before assigning product cause.",
        ]
    if category == "careers_site":
        return ["Ask for job posting URLs, screenshots, and recent page template changes."]
    if category == "candidate_import":
        return ["Ask for the import job ID and sanitized sample rows for missing candidates."]
    return ["Ask for scope, timing, and visible symptoms."]
