"""Response generator node. Builds the reply using ONLY chunks that passed the
grader — failed/ungraded chunks never reach the LLM. The exact prompt is stored
on the state so it lands in ai_logs.prompt_text (audit telemetry fix)."""
from __future__ import annotations

import json

from app.core.logging import logger
from app.services.llm_service import complete
from app.services.prompt_builder import build_messages
from app.services.workflow.types import WorkflowState


async def response_generator(state: WorkflowState) -> WorkflowState:
    state.node_history.append("RESPONSE_GENERATOR")
    passed = state.passed_chunks
    if not passed:
        state.errors.append("no graded chunks passed — generator skipped")
        return state

    context = [
        {"brand": state.brand_name, "text": g.chunk.content,
         "policy_type": g.chunk.category, "source": g.chunk.source}
        for g in passed
    ]
    messages = build_messages(state.brand_name, state.customer_message, context)
    if state.order_context:
        messages[-1]["content"] += f"\n\nOrder context (this customer only):\n{json.dumps(state.order_context)}"

    state.prompt_text = json.dumps(messages)

    try:
        reply = await complete(messages)
    except Exception as exc:  # noqa: BLE001
        state.errors.append(f"generation failed: {exc}")
        return state

    state.generated_response = reply.strip()
    # Citations: source URLs of the chunks that were actually used.
    state.citations = [g.chunk.source for g in passed if g.chunk.source and g.chunk.source != "manual"]
    return state