"""Self-correction node. On validation failure, rewrites the draft addressing
the reviewer's specific issues — ONE correction pass, source-chunks only."""
from __future__ import annotations

import json

from app.core.logging import logger
from app.services.llm_service import complete
from app.services.workflow.types import WorkflowState

_MAX_RETRIES = 1


async def self_correction_node(state: WorkflowState) -> WorkflowState:
    state.node_history.append("SELF_CORRECTION")
    if state.correction_attempts >= _MAX_RETRIES:
        return state

    vr = state.validation_result
    if not vr or not vr.issues:
        return state

    chunks = "\n\n".join(f"[{i}] {g.chunk.content[:450]}" for i, g in enumerate(state.passed_chunks))
    messages = [
        {"role": "system", "content": "You rewrite a support reply fixing ONLY the listed issues. "
                                      "Never add information that is not in the source documents."},
        {"role": "user", "content": (
            f"You generated this reply:\n{state.generated_response}\n\n"
            f"Reviewer issues: {json.dumps(vr.issues)}\n"
            f"Correction hint: {vr.correction_hint or 'none'}\n\n"
            f"Source documents (your only allowed source):\n{chunks}\n\n"
            "Rewrite the reply.")},
    ]
    try:
        corrected = await complete(messages)
    except Exception as exc:  # noqa: BLE001
        state.errors.append(f"self-correction failed: {exc}")
        return state

    state.generated_response = corrected.strip()
    state.correction_attempts += 1
    return state