"""Escalation node — the human gate. The workflow never sends anything itself;
failing paths land here with an explicit reason, and the conversation is
routed to the human review queue."""
from __future__ import annotations

from app.services.workflow.types import WorkflowState

_ESCALATION_REPLY = (
    "Thank you for reaching out. I want to make sure you get accurate information "
    "on this, so let me connect you with a specialist who can help directly."
)


async def escalate_node(state: WorkflowState, reason: str) -> WorkflowState:
    state.node_history.append(f"ESCALATE:{reason}")
    state.errors.append(f"escalation reason: {reason}")
    state.final_status = "escalated"
    state.final_response = _ESCALATION_REPLY
    return state