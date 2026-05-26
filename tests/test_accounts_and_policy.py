from __future__ import annotations

import io
from urllib.error import HTTPError

import hirenest_support.discord as discord
from hirenest_support.accounts import get_account_context
from hirenest_support.discord import send_discord_escalation_message
from hirenest_support.policy import recommend_escalation


def test_apex_account_context_includes_premier_sla() -> None:
    context = get_account_context("Apex Robotics has candidate invitation delivery impact.")

    assert context["found"] is True
    assert context["account"]["customer_name"] == "Apex Robotics"
    assert context["contract"]["support_tier"] == "Premier"
    assert any(row["severity"] == "SEV2" for row in context["sla"])


def test_case_a_policy_escalates_to_messaging_platform() -> None:
    recommendation = recommend_escalation(
        "Apex Robotics interview invitation emails are not delivered to all candidates. "
        "Premier support and business impact."
    )

    assert recommendation["severity"] == "SEV2"
    assert recommendation["should_escalate"] is True
    assert recommendation["team"] == "Messaging Platform"
    assert recommendation["sla"]["first_response"] == "30 minutes"


def test_candidate_import_policy_uses_data_import_operations() -> None:
    recommendation = recommend_escalation(
        "Evergreen Retail CSV import is missing candidate phone numbers."
    )

    assert recommendation["severity"] == "SEV3"
    assert recommendation["team"] == "Data Import Operations"
    assert "Import job ID" in recommendation["additional_info_needed"]


def test_discord_escalation_tool_dry_runs_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("HIRENEST_DISCORD_WEBHOOK_URL", raising=False)

    result = send_discord_escalation_message(
        "Candidate invitation delivery is broadly affected.",
        "SEV2",
        "Messaging Platform",
        "Apex Robotics",
    )

    assert result["sent"] is False
    assert result["dry_run"] is True
    assert "HireNest escalation" in result["content"]


def test_discord_escalation_tool_uses_webhook_url_only(monkeypatch) -> None:
    captured = {}

    def fake_post_json(url, payload, headers=None):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"sent": True, "status": 204, "response": ""}

    monkeypatch.setenv("HIRENEST_DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.delenv("HIRENEST_DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("HIRENEST_DISCORD_CHANNEL_ID", raising=False)
    monkeypatch.setattr(discord, "_post_json", fake_post_json)

    result = send_discord_escalation_message(
        "Candidate invitation delivery is broadly affected.",
        "SEV2",
        "Messaging Platform",
        "Apex Robotics",
    )

    assert result["sent"] is True
    assert captured["url"] == "https://discord.example/webhook"
    assert captured["headers"] is None
    assert "HireNest escalation" in captured["payload"]["content"]


def test_discord_post_json_returns_http_error_payload(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise HTTPError(
            "https://discord.example/webhook",
            403,
            "Forbidden",
            hdrs={},
            fp=io.BytesIO(b'{"message":"Forbidden"}'),
        )

    monkeypatch.setattr(discord.request, "urlopen", forbidden)

    result = discord._post_json("https://discord.example/webhook", {"content": "test"})

    assert result == {
        "sent": False,
        "status": 403,
        "response": '{"message":"Forbidden"}',
        "error": "Forbidden",
    }


def test_discord_post_json_sends_discord_api_headers(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b""

    def fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        captured["headers"] = dict(req.header_items())
        return FakeResponse()

    monkeypatch.delenv("HIRENEST_DISCORD_USER_AGENT", raising=False)
    monkeypatch.setattr(discord.request, "urlopen", fake_urlopen)

    result = discord._post_json("https://discord.example/webhook", {"content": "test"})

    assert result["sent"] is True
    assert captured["timeout"] == 10
    assert captured["headers"]["Accept"] == "application/json"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["headers"]["User-agent"].startswith("DiscordBot (")
