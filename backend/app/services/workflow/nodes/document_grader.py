"""Document grader node. Decides which retrieved/scraped chunks are actually
relevant to the customer's question. Uses ONE batched LLM call when enabled;
falls back to the deterministic retrieval score otherwise. Every decision
(failed included) is kept in state.graded_chunks for the audit trail."""
from __future__ import annotations

import json

from app.core.config import settings
from app.core.logging import logger
from app.services.llm_service import complete
from app.services.workflow.types import GradedChunk, KBChunk, WorkflowState

_FALLBACK_THRESHOLD = 0.50  # used when the LLM grader is disabled/unavailable


def _safe_float(value, default: float = 0.0) -> float:
    """Coerce an LLM-reported score safely; anything non-numeric -> default."""
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    return default if not 0.0 <= score <= 1.0 else score


def _safe_bool(value) -> bool:
    """Treat literal strings like 'false'/'no' the way a boolean parse should."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return False


async def _batch_grade_llm(state: WorkflowState) -> list[dict]:
    blobs = "\n\n".join(
        f"[{i}] (score {c.score:.2f}) {c.content[:450]}" for i, c in enumerate(state.retrieved_chunks)
    )
    messages = [
        {"role": "system", "content": (
            "You grade whether a support document helps answer a customer question. "
            "Reply with ONLY valid JSON, one object per document: "
            "[{\"index\": <int>, \"relevant\": true/false, \"score\": <0.0-1.0>, \"reason\": \"one sentence\"}]")},
        {"role": "user", "content": (
            f"Customer question: {state.customer_message}\n\n"
            f"{blobs}\n\nReturn the JSON array.")},
    ]
    try:
        raw = await complete(messages)
        parsed = json.loads(raw.strip())
        return [entry for entry in parsed if isinstance(entry, dict)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("grader LLM failed (%s); using retrieval score fallback", exc)
        return []


def _grade_from_scores(chunks: list[KBChunk], llm_grades: list[dict]) -> list[GradedChunk]:
    # Build a validated index->grade map; out-of-range or malformed indices
    # are simply ignored and those chunks fall back to the retrieval score.
    score_map: dict[int, dict] = {}
    for g in llm_grades:
        idx = g.get("index")
        if isinstance(idx, str) and idx.isdigit():
            idx = int(idx)
        if isinstance(idx, int) and 0 <= idx < len(chunks):
            score_map[idx] = g

    graded: list[GradedChunk] = []
    for i, c in enumerate(chunks):
        g = score_map.get(i)
        if g:
            llm_score = _safe_float(g.get("score"))
            passed = _safe_bool(g.get("relevant")) and llm_score >= 0.60
            graded.append(GradedChunk(
                chunk=c, passed=passed,
                grader_score=llm_score,
                grader_reason=str(g.get("reason") or "")[:300],
            ))
        else:
            score = _safe_float(c.score)
            passed = score >= _FALLBACK_THRESHOLD
            graded.append(GradedChunk(
                chunk=c, passed=passed,
                grader_score=round(score, 4),
                grader_reason="retrieval score fallback (LLM grader unavailable)",
            ))
    return graded


async def document_grader(state: WorkflowState) -> WorkflowState:
    state.node_history.append("DOCUMENT_GRADER")
    if not state.retrieved_chunks:
        return state

    llm_grades: list[dict] = []
    if settings.workflow_grader_enabled:
        llm_grades = await _batch_grade_llm(state)

    state.graded_chunks = _grade_from_scores(state.retrieved_chunks, llm_grades)
    return state