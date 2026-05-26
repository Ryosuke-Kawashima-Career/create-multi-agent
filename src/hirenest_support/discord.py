from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

_DEFAULT_USER_AGENT = "DiscordBot (https://hirenest.example/support-escalation, 0.1)"


def send_discord_escalation_message(
    case_summary: str,
    severity: str,
    team: str,
    customer: str = "Unknown",
) -> dict[str, Any]:
    """Send an internal escalation message to Discord.

    Configure HIRENEST_DISCORD_WEBHOOK_URL. Without a webhook URL the function returns
    a dry-run payload so the workshop remains safe by default.
    """
    content = _format_message(case_summary, severity, team, customer)
    webhook_url = os.getenv("HIRENEST_DISCORD_WEBHOOK_URL", "").strip()

    dry_run = os.getenv("HIRENEST_DISCORD_DRY_RUN", "").lower() in {"1", "true", "yes"}
    if dry_run or not webhook_url:
        return {
            "sent": False,
            "dry_run": True,
            "reason": "Discord webhook URL is not configured or dry-run is enabled.",
            "content": content,
        }

    return _post_json(webhook_url, {"content": content})


def _format_message(case_summary: str, severity: str, team: str, customer: str) -> str:
    summary = case_summary.strip()
    if len(summary) > 1200:
        summary = summary[:1197].rstrip() + "..."
    return "\n".join(
        [
            f"**HireNest escalation** | {severity} | {team}",
            f"Customer: {customer}",
            "",
            summary,
        ]
    )


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": os.getenv("HIRENEST_DISCORD_USER_AGENT", _DEFAULT_USER_AGENT),
            **(headers or {}),
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            text = response.read().decode("utf-8")
            return {
                "sent": 200 <= response.status < 300,
                "status": response.status,
                "response": text,
            }
    except error.HTTPError as exc:
        return {
            "sent": False,
            "status": exc.code,
            "response": exc.read().decode("utf-8", errors="replace"),
            "error": exc.reason,
        }
    except error.URLError as exc:
        return {
            "sent": False,
            "status": None,
            "response": "",
            "error": str(exc.reason),
        }
