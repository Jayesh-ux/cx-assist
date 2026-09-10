"""Response validator node. Deterministic guardrails always run (grounding,
fallback phrase, confidence vs the configured threshold). When
workflow_llm_reviewer_enabled is on, an extra adversarial LLM pass reviews the
draft against the source chunks before approval."""
from __future__ import annotations

import json

from app.core.config import settings
from app.core.guardrails import finalize_reply
from app.core.logging import logger
from app.services.llm_service import complete
from app.services.workflow.types import ValidationResult, WorkflowState

_REVIEWER_PROMPT = (
    "You are an adversarial reviewer of a customer-support reply.\n"
    "Source documents:\n{chunks}\n\n"
    "Generated response:\n{reply}\n\n"
    "Check: (1) does the response claim anything NOT in the source docs, "
    "(2) does it promise anything the policy does not allow, "
    "(3) is it factually consistent with the sources.\n"
    "Reply with only valid JSON: "
    "{{\"valid\": true/false, \"issues\": [\"specific issues\"], \"correction_hint\": \"what to fix\"}}"
)


async def _adversarial_review(state: WorkflowState) -> tuple[bool, list[str], str]:
    chunks = "\n\n".join(f"[{i}] {g.chunk.content[:450]}" for i, g in enumerate(state.passed_chunks))
    messages = [
        {"role": "system", "content": "You only reply with valid JSON."},
        {"role": "user", "content": _REVIEWER_PROMPT.format(chunks=chunks, reply=state.generated_response or "")},
    ]
    try:
        raw = await complete(messages)
        data = json.loads(raw.strip())
        return bool(data.get("valid")), list(data.get("issues") or []), str(data.get("correction_hint") or "")
    except Exception as exc:  # noqa: BLE001
        logger.warning("adversarial reviewer failed (%s); skipping", exc)
        return True, [], ""


async def response_validator(state: WorkflowState) -> WorkflowState:
    state.node_history.append("RESPONSE_VALIDATOR")
    reply = state.generated_response
    passed = state.passed_chunks

    if not reply or not passed:
        state.validation_result = ValidationResult(False, ["no grounded response to validate"], "retry generation")
        return state

    top_score = max((g.chunk.score for g in passed), default=0.0)
    state.confidence_score = round(min(0.9 * top_score + 0.1, 1.0), 4)

    # Deterministic guardrails: grounding + fallback phrase + config-driven threshold.
    grv = finalize_reply(reply, state.confidence_score, has_context=True)
    issues = []
    if not grv.ok:
        issues.append(grv.reason or grv.code.value)

    valid = grv.ok
    correction_hint = ""
    if valid and settings.workflow_llm_reviewer_enabled:
        ok, llm_issues, hint = await _adversarial_review(state)
        if not ok:
            valid = False
            correction_hint = hint
            issues.extend(llm_issues)
    elif not valid:
        hint_ = f"grounding failed: {grv.reason}" if not grv.ok else ""
        state.validation_result = ValidationResult(False, issues, correction_hint=hint_)
        return state

    state.validation_result = ValidationResult(valid, issues, correction_hint=correction_hint)
    return state