from __future__ import annotations

from typing import Any

from hirenest_support.loaders import load_jsonl
from hirenest_support.paths import DATA_DIR


def search_ticket_history(query: str, limit: int = 4) -> list[dict[str, Any]]:
    # TODO
    return []


def get_ticket_thread(ticket_id: str) -> dict[str, Any]:
    """Return the full fixture thread for a ticket after search identifies it."""
    ticket = next(
        (record for record in _load_ticket_records() if record["ticket_id"] == ticket_id),
        None,
    )
    if not ticket:
        return {"found": False, "ticket_id": ticket_id, "comments": []}
    return {
        "found": True,
        "ticket": ticket,
        "comments": _load_comments(ticket_id),
        "escalations": [
            row
            for row in load_jsonl("tickets/escalated_cases.jsonl")
            if row.get("source_ticket_id") == ticket_id or row.get("ticket_id") == ticket_id
        ],
    }


def _load_ticket_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((DATA_DIR / "tickets").glob("20*.jsonl")):
        for record in load_jsonl(str(path.relative_to(DATA_DIR))):
            records.append(record)
    return records


def _enrich_ticket(record: dict[str, Any], score: int) -> dict[str, Any]:
    ticket_id = record["ticket_id"]
    return {
        **record,
        "match_score": score,
        "comments": _load_comments(ticket_id)[:2],
        "applicable_insight": _insight(record),
    }


def _load_comments(ticket_id: str) -> list[dict[str, Any]]:
    comments_path = DATA_DIR / "tickets" / "ticket_comments" / f"{ticket_id}-comments.jsonl"
    if comments_path.exists():
        return load_jsonl(str(comments_path.relative_to(DATA_DIR)))
    return []


def _insight(record: dict[str, Any]) -> str:
    category = record.get("category")
    if category == "candidate_communication":
        return (
            "Prior invitation-email cases show deliverability, template tokens, "
            "and suppression-list checks need to be reviewed together."
        )
    if category == "calendar_integration":
        return (
            "Prior calendar cases show OAuth scopes, free/busy visibility, "
            "and interviewer working hours are the fastest comparison points."
        )
    if category == "careers_site":
        return (
            "Prior careers-site cases show published job state, form embed version, "
            "and custom domain cache need to be checked before escalation."
        )
    if category == "scorecard_permissions":
        return "Prior scorecard cases usually hinge on interviewer role, stage, and form sharing."
    if category == "candidate_import":
        return "Prior import cases show CSV mapping, dedupe rules, and required fields drive fixes."
    return (
        "Use the prior cause and resolution as comparison points, "
        "but confirm current incident status."
    )
