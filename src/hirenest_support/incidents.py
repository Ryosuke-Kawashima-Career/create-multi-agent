from __future__ import annotations

from typing import Any

from hirenest_support.intake import parse_case
from hirenest_support.loaders import load_json, load_jsonl
from hirenest_support.text import score_text, text_from_record


def correlate_incidents(query: str, limit: int = 4) -> dict[str, Any]:
    intake = parse_case(query)
    active = load_json("incidents/active_incidents.json")
    historical = load_jsonl("incidents/historical_incidents_2025.jsonl") + load_jsonl(
        "incidents/historical_incidents_2026.jsonl"
    )
    status_updates = load_jsonl("incidents/status_page_updates.jsonl")

    active_matches = _rank(query, active, intake.category, limit)
    historical_matches = _rank(query, historical, intake.category, limit)
    likely_related = bool(active_matches and active_matches[0]["match_score"] >= 10)

    related_status = []
    if active_matches:
        active_ids = {match["incident_id"] for match in active_matches}
        related_status = [
            update for update in status_updates if update.get("incident_id") in active_ids
        ]

    return {
        "likely_related": likely_related,
        "assessment": _assessment(likely_related, intake.category),
        "active_matches": active_matches,
        "historical_matches": historical_matches,
        "status_updates": related_status,
    }


def get_incident_timeline(incident_id: str) -> dict[str, Any]:
    """Return internal timeline entries for a known incident ID."""
    path = f"incidents/incident_timelines/{incident_id}.jsonl"
    try:
        return {
            "found": True,
            "incident_id": incident_id,
            "timeline": load_jsonl(path),
            "customer_safe": False,
        }
    except FileNotFoundError:
        return {"found": False, "incident_id": incident_id, "timeline": [], "customer_safe": False}


def _rank(
    query: str, records: list[dict[str, Any]], category: str, limit: int
) -> list[dict[str, Any]]:
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        score = score_text(query, text_from_record(record), boosts=[category])
        services = " ".join(record.get("services", record.get("affected_services", [])))
        if category and category in services:
            score += 5
        elif category and category != "general" and services:
            score -= 20
        if score >= 12:
            scored.append((score, record))
    ranked = sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
    return [{**record, "match_score": score} for score, record in ranked]


def _assessment(likely_related: bool, category: str) -> str:
    if likely_related:
        return (
            "Likely related to an active HireNest ATS incident; "
            "engineering confirmation is required."
        )
    if category == "candidate_import":
        return (
            "No active service incident correlation expected; "
            "treat as customer-specific data import investigation."
        )
    return (
        "No strong active incident match; continue checking customer-specific "
        "configuration and logs."
    )
