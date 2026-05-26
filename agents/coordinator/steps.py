from __future__ import annotations

from typing import Any

from google.adk.agents.context import Context
from google.adk.events import RequestInput
from google.adk.events.event import Event
from google.adk.workflow import DEFAULT_ROUTE

from agents.coordinator.constants import (
    INVESTIGATION_AGENT_NAMES,
    ROUTE_RETRY,
    STATE_CLARIFICATION_QUESTIONS,
    STATE_CLARIFICATION_REQUEST,
    STATE_ESCALATION_POLICY,
    STATE_INVESTIGATION_PLAN,
    STATE_SYNTHESIS_BRIEF,
)
from agents.coordinator.schemas import InvestigationPlan
from hirenest_support.communication import generate_customer_response_package
from hirenest_support.policy import recommend_escalation


def _event_text(event: Event) -> str:
    if not event.content or not event.content.parts:
        return ""
    return "".join(part.text for part in event.content.parts if part.text).strip()


def _latest_text_by_author(ctx: Context, author: str) -> str:
    for event in reversed(ctx.session.events):
        if event.invocation_id != ctx.invocation_id or event.author != author:
            continue
        text = _event_text(event)
        if text:
            return text
    return ""


def _session_user_messages(ctx: Context) -> list[str]:
    messages: list[str] = []
    for event in ctx.session.events:
        if event.author != "user":
            continue
        text = _event_text(event)
        if text:
            messages.append(text)
    return messages


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return repr(value)


def _canonical_agent_name(name: str) -> str:
    for agent_name in INVESTIGATION_AGENT_NAMES:
        if agent_name in name:
            return agent_name
    return name


def _format_joined_findings(node_input: Any) -> str:
    if not isinstance(node_input, dict):
        return _stringify(node_input)

    sections: list[str] = []
    for name, value in node_input.items():
        sections.append(f"{_canonical_agent_name(name)} findings:\n{_stringify(value)}")
    return "\n\n".join(sections)


def _format_clarification_request(questions: list[str]) -> str:
    formatted_questions = "\n".join(f"- {question}" for question in questions)
    return (
        "I need a little more information before running the support investigation:\n"
        f"{formatted_questions}"
    )


def route_investigation_plan(ctx: Context, node_input: InvestigationPlan):
    # TODO
    raise NotImplementedError("TODO")


def request_retry_clarification(ctx: Context, node_input: Any):
    # TODO
    raise NotImplementedError("TODO")


def build_retry_planning_input(ctx: Context, node_input: Any) -> str:
    # TODO
    raise NotImplementedError("TODO")


def build_synthesis_input(ctx: Context, node_input: Any) -> str:
    customer_messages = "\n\n".join(_session_user_messages(ctx))
    plan = _latest_text_by_author(ctx, "triage_planning_agent")
    if not plan:
        plan = _stringify(ctx.state.get(STATE_INVESTIGATION_PLAN, ""))
    findings = _format_joined_findings(node_input)
    return "\n\n".join(
        [
            "Customer inquiry and session context:",
            customer_messages,
            "Triage / Investigation Plan:",
            plan,
            "Parallel specialist findings:",
            findings,
        ]
    )


def _planned_value(ctx: Context, field_name: str, default: str = "Unknown") -> str:
    plan = ctx.state.get(STATE_INVESTIGATION_PLAN, {})
    if not isinstance(plan, dict):
        return default
    value = plan.get(field_name)
    return _stringify(value) or default


def _format_escalation_policy(policy: dict[str, Any]) -> str:
    sla = policy.get("sla") or {}
    return "\n\n".join(
        [
            "## Escalation Policy Check",
            "\n".join(
                [
                    f"- Recommended severity: {policy.get('severity', 'Unknown')}",
                    f"- Reasoning: {policy.get('severity_reason', 'Unknown')}",
                    f"- SLA response deadline: {sla.get('first_response', 'Unknown')}",
                    f"- SLA update frequency: {sla.get('update_frequency', 'Unknown')}",
                    f"- Escalate: {'Yes' if policy.get('should_escalate') else 'No'}",
                    f"- Recommended team: {policy.get('team', 'Unknown')}",
                    f"- Escalation reason: {policy.get('reason', 'Unknown')}",
                    f"- Attach: {', '.join(policy.get('attach', [])) or 'None'}",
                    "- Additional information needed: "
                    f"{', '.join(policy.get('additional_info_needed', [])) or 'None'}",
                    "- Customer-safe constraints: "
                    f"{'; '.join(policy.get('customer_safe_constraints', [])) or 'None'}",
                ]
            ),
        ]
    )


def _format_policy_agent_output(policy_output: Any) -> str:
    if isinstance(policy_output, dict):
        if "severity" in policy_output or "should_escalate" in policy_output:
            return _format_escalation_policy(policy_output)
        for key in ["policy", "escalation_policy", "result", "output"]:
            value = policy_output.get(key)
            if isinstance(value, dict):
                return _format_policy_agent_output(value)
            if isinstance(value, str) and value.strip():
                return value.strip()
    text = _stringify(policy_output)
    return text if text else "Escalation policy agent returned no policy output."


def _format_customer_communication(response_package: dict[str, Any]) -> str:
    disclosure = response_package.get("disclosure_check", {})
    return "\n\n".join(
        [
            "## Customer Communication Draft",
            "\n".join(
                [
                    f"Subject: {response_package.get('subject', 'Update on your support case')}",
                    "",
                    _stringify(response_package.get("customer_response", "")),
                ]
            ),
            "## Customer Communication Safety Check",
            "\n".join(
                [
                    "- Disclosure safe to send: "
                    f"{'Yes' if disclosure.get('safe_to_send') else 'No'}",
                    "- Omitted or softened internal details: "
                    f"{'Yes' if disclosure.get('omitted_or_softened') else 'No'}",
                    "- Requires human review: "
                    f"{'Yes' if response_package.get('requires_human_review') else 'No'}",
                    "- Human review reason: "
                    f"{', '.join(response_package.get('human_review_reason', [])) or 'None'}",
                    "- Assumptions: "
                    f"{'; '.join(response_package.get('assumptions', [])) or 'None'}",
                ]
            ),
        ]
    )


def build_escalation_policy_input(ctx: Context, node_input: Any) -> str:
    customer_messages = "\n\n".join(_session_user_messages(ctx))
    synthesis = _stringify(node_input)
    ctx.state[STATE_SYNTHESIS_BRIEF] = synthesis
    return "\n\n".join(
        [
            "Evaluate escalation policy for this HireNest ATS support case.",
            "Return severity, SLA, should_escalate, recommended team, required attachments, "
            "missing information, customer-safe constraints, and Discord notification result "
            "when escalation is required.",
            "Customer inquiry and session context:",
            customer_messages,
            "Synthesis / hypothesis update:",
            synthesis,
        ]
    )


def build_final_package_input(ctx: Context, node_input: Any) -> str:
    customer_messages = "\n\n".join(_session_user_messages(ctx))
    synthesis = _stringify(ctx.state.get(STATE_SYNTHESIS_BRIEF, ""))
    policy_agent_output = node_input
    policy_text = _format_policy_agent_output(policy_agent_output)

    # Keep deterministic structured state for tests and local communication drafting when the
    # remote A2A output is natural language rather than a tool-returned dict.
    policy = recommend_escalation("\n\n".join([customer_messages, synthesis]))
    ctx.state[STATE_ESCALATION_POLICY] = policy
    communication_source = "\n\n".join(
        [
            "# Coordinator Support Brief",
            "## Case Summary",
            "\n".join(
                [
                    f"- Inquiry summary: {customer_messages}",
                    f"- Impact scope: {_planned_value(ctx, 'business_impact')}",
                    f"- Problem category: {_planned_value(ctx, 'case_category')}",
                    f"- Initial urgency: {_planned_value(ctx, 'urgency')}",
                ]
            ),
            "## Synthesis / Hypothesis Update",
            synthesis,
            "## Escalation Policy Agent Output",
            policy_text,
            _format_escalation_policy(policy),
        ]
    )
    response_package = generate_customer_response_package(communication_source)

    return "\n\n".join(
        [
            "Output language requirement:",
            (
                "Write the final response in the same language as the Customer inquiry "
                "and session context. Apply this to section headings, summaries, the "
                "customer communication draft, clarification questions, and internal next "
                "steps. Translate or rewrite English intermediate text as needed. Keep "
                "product names, severity codes, SLA values, IDs, and team names unchanged."
            ),
            "Customer inquiry and session context:",
            customer_messages,
            "Synthesis / hypothesis update:",
            synthesis,
            "Escalation policy check from escalation_policy_agent:",
            policy_text,
            "Deterministic policy state used for communication safety checks:",
            _format_escalation_policy(policy),
            "Customer communication draft:",
            _format_customer_communication(response_package),
        ]
    )
