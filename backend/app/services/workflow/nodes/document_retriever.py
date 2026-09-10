"""Document retriever node. Wraps the existing brand-scoped vector_store query.
Never retrieves across brands — the store already filters by the brand, and we
re-assert the scope on every result before it enters the state."""
from __future__ import annotations

from app.core.logging import logger
from app.services import vector_store
from app.services.workflow.types import KBChunk, WorkflowState


async def document_retriever(state: WorkflowState, top_k: int | None = None) -> WorkflowState:
    state.node_history.append("DOCUMENT_RETRIEVER")
    try:
        rows = vector_store.query(brand=state.brand_name, query_text=state.customer_message, top_k=top_k or 5)
    except Exception as exc:  # noqa: BLE001
        state.errors.append(f"retrieval failed: {exc}")
        return state

    for i, r in enumerate(rows):
        # Brand isolation re-check at the workflow layer.
        if r.get("brand") and r["brand"] != state.brand_name:
            logger.warning("retriever returned cross-brand chunk brand=%s for state=%s", r["brand"], state.brand_id)
            continue
        state.retrieved_chunks.append(KBChunk(
            id=f"{state.brand_id}-c{i}-{hash(str(r.get('source', '')) + str(i))}",
            title=r.get("source", ""),
            content=r.get("text", ""),
            category=r.get("policy_type", "faq"),
            score=float(r.get("score", 0.0)),
            source=r.get("source", ""),
        ))
    return state