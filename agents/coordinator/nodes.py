from __future__ import annotations

from google.adk import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.workflow import JoinNode

from agents._common import model_name, runtime_a2a_httpx_client, specialist_card_url
from agents.coordinator.schemas import InvestigationPlan

_remote_a2a_httpx_client = runtime_a2a_httpx_client()

triage_planning_agent = Agent(
    name="triage_planning_agent",
    model=model_name(),
    description="Classifies the support case and creates an adaptive investigation plan.",
    output_schema=InvestigationPlan,
    instruction=(
        "You are the Triage / Planning Agent for HireNest ATS Support. "
        "Read the customer inquiry and any prior user turns in the session. "
        "Return an InvestigationPlan. Classify the case, identify urgency and business "
        "impact, list initial hypotheses, and produce specialist directives for Account "
        "Context, Ticket History, Incident Status, Knowledge Base, and Diagnostics. "
        "Use your judgment to decide what each specialist should focus on. "
        "If the customer, affected workflow, impact scope, or symptom is too ambiguous to "
        "investigate, set ready_for_investigation=false and include concrete clarification "
        "questions. Do not fabricate missing facts."
    ),
    mode="single_turn",
)

account_context_agent = RemoteA2aAgent(
    name="account_context_agent",
    agent_card=specialist_card_url("ACCOUNT_CONTEXT_A2A_URL", "http://localhost:8103"),
    httpx_client=_remote_a2a_httpx_client,
    description="Looks up customer account, contract, entitlement, SLA, and health context.",
    use_legacy=False,
)
ticket_history_agent = RemoteA2aAgent(
    name="ticket_history_agent",
    agent_card=specialist_card_url("TICKET_HISTORY_A2A_URL", "http://localhost:8101"),
    httpx_client=_remote_a2a_httpx_client,
    description="Finds similar support tickets and historical resolutions.",
    use_legacy=False,
)
incident_status_agent = RemoteA2aAgent(
    name="incident_status_agent",
    agent_card=specialist_card_url("INCIDENT_STATUS_A2A_URL", "http://localhost:8104"),
    httpx_client=_remote_a2a_httpx_client,
    description="Checks active and historical incidents for correlation.",
    use_legacy=False,
)
knowledge_base_agent = RemoteA2aAgent(
    name="knowledge_base_agent",
    agent_card=specialist_card_url("KNOWLEDGE_BASE_A2A_URL", "http://localhost:8102"),
    httpx_client=_remote_a2a_httpx_client,
    description="Finds FAQ, troubleshooting, runbook, product, and policy references.",
    use_legacy=False,
)
diagnostics_agent = RemoteA2aAgent(
    name="diagnostics_agent",
    agent_card=specialist_card_url("DIAGNOSTICS_A2A_URL", "http://localhost:8107"),
    httpx_client=_remote_a2a_httpx_client,
    description="Suggests diagnostic checks, evidence gaps, and next troubleshooting probes.",
    use_legacy=False,
)
escalation_policy_agent = RemoteA2aAgent(
    name="escalation_policy_agent",
    agent_card=specialist_card_url("ESCALATION_POLICY_A2A_URL", "http://localhost:8105"),
    httpx_client=_remote_a2a_httpx_client,
    description="Applies severity, SLA, escalation, and customer communication policy.",
    use_legacy=False,
)
parallel_investigation_join = JoinNode(name="parallel_investigation_join")

synthesis_hypothesis_agent = Agent(
    name="synthesis_hypothesis_agent",
    model=model_name(),
    description="Synthesizes parallel findings and updates the working hypotheses.",
    instruction=(
        "You are the Synthesis / Hypothesis Update Agent for HireNest ATS Support. "
        "Use the triage plan and all parallel specialist findings. "
        "Update the hypotheses, explain which evidence supports or weakens each hypothesis, "
        "identify whether clarification is needed, and prepare an internal support brief. "
        "Do not make final severity or customer-response decisions; those are handled later."
    ),
    mode="single_turn",
)

final_package_agent = Agent(
    name="support_case_resolution_package_agent",
    model=model_name(),
    description="Generates the final Support Case Resolution Package.",
    instruction=(
        "You are the Support Case Resolution Package Agent for HireNest. "
        "Combine the synthesis, escalation policy check, and customer communication draft. "
        "Follow the Output language requirement in the input. Do not default to English "
        "just because intermediate evidence or templates are in English. Preserve product "
        "names, severity codes, SLA values, IDs, and team names. "
        "Produce the final package with these sections: Case Summary, Triage / Planning, "
        "Parallel Investigation Findings, Hypothesis Update, Escalation Policy Check, "
        "Customer Communication Draft, Clarification Questions, and Internal Next Steps. "
        "Never include raw logs, internal-only timelines, tenant IDs, or sensitive account "
        "value and health signals in customer-facing text."
    ),
    mode="single_turn",
)
