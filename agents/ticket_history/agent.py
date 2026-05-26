from __future__ import annotations

from google.adk import Agent

from agents._common import build_a2a_app, model_name
from hirenest_support.tickets import get_ticket_thread, search_ticket_history


def search_similar_tickets(inquiry: str) -> dict:
    """Search similar historical tickets and return causes, resolutions, and insights."""
    return {"similar_tickets": search_ticket_history(inquiry)}


def retrieve_ticket_thread(ticket_id: str) -> dict:
    """Retrieve comments and escalation records for a specific historical ticket."""
    return get_ticket_thread(ticket_id)


root_agent = Agent(
    name="ticket_history_agent",
    model=model_name(),
    description="Searches HireNest historical support tickets and escalation cases.",
    instruction="TODO",
    tools=[],  # TODO
)

app = build_a2a_app(root_agent, default_port=8101)
