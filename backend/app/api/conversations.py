"""Conversation & reply-generation pipeline.

Core flow (all brand-isolated):
  customer message -> (auth) -> brand detect -> conversation created -> customer message stored
  -> order lookup (THIS customer only) -> stateful workflow (retrieve -> grade ->
     scrape-fallback -> generate -> validate -> self-correct -> escalate)
  -> guardrail confidence -> review routing -> AILog + audit.
NOTE: no `from __future__ import annotations` — slowapi's wrapper needs the
generate endpoint signature resolvable at route-registration time.
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import can_access_brand, require_agent, scoped_brand_id
from app.core.config import settings
from app.core.guardrails import ValidationCode
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.ai_log import AILog
from app.models.brand import Brand
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.order import Order
from app.models.user import User
from app.schemas.schemas import ConversationCreateNew, GenerateReply
from app.services.brand_detect import detect_brand
from app.services.llm_service import last_provider
from app.services.workflow.runner import run_cx_workflow
from app.services.workflow.types import WorkflowState

router = APIRouter()


def _brand_or_404(db: Session, brand_id: str) -> Brand:
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    return brand


def _require_brand_access(user: User, brand_id: str) -> None:
    if not can_access_brand(user, brand_id):
        raise HTTPException(403, "You do not have access to this brand")


@router.post("", status_code=201)
def create_conversation(payload: ConversationCreateNew, db: Session = Depends(get_db),
                        current_user: User = Depends(require_agent)):
    brand = _brand_or_404(db, payload.brand_id)
    _require_brand_access(current_user, brand.id)
    customer = None
    if payload.customer_email:
        customer = db.query(Customer).filter(
            Customer.brand_id == brand.id, Customer.email == payload.customer_email.lower()).first()
        if not customer:
            customer = Customer(brand_id=brand.id, email=payload.customer_email.lower())
            db.add(customer)
            db.flush()
    conv = Conversation(brand_id=brand.id, customer_id=customer.id if customer else None,
                        detected_brand_name=brand.name, status="open")
    db.add(conv)
    db.flush()
    db.add(Message(conversation_id=conv.id, brand_id=brand.id, role="customer", content=payload.customer_message))
    db.commit()
    return conv.to_dict()


@router.get("")
def list_conversations(db: Session = Depends(get_db), current_user: User = Depends(require_agent)):
    q = db.query(Conversation)
    if scoped := scoped_brand_id(current_user):
        q = q.filter(Conversation.brand_id == scoped)
    convs = q.order_by(Conversation.created_at.desc()).limit(100).all()
    return [c.to_dict() for c in convs]


@router.get("/{conv_id}")
def get_conversation(conv_id: str, db: Session = Depends(get_db),
                     current_user: User = Depends(require_agent)):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    _require_brand_access(current_user, conv.brand_id)
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return {"conversation": conv.to_dict(), "messages": [m.to_dict() for m in msgs]}


@router.get("/{conv_id}/history")
def conversation_history(conv_id: str, db: Session = Depends(get_db),
                         current_user: User = Depends(require_agent)):
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise HTTPException(404, "Conversation not found")
    _require_brand_access(current_user, conv.brand_id)
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content or m.final_text or m.draft_text or ""} for m in msgs]


@router.post("/generate")
@limiter.limit("20/minute")
async def generate_reply(request: Request, payload: GenerateReply, db: Session = Depends(get_db),
                         current_user: User = Depends(require_agent)):
    brand = _brand_or_404(db, payload.brand_id)
    _require_brand_access(current_user, brand.id)
    request_id = getattr(request.state, "request_id", "unknown")

    # 1) brand detect + ENFORCE isolation (blocks, not just logs)
    brands_all = [b.name for b in db.query(Brand).all()]
    detected = detect_brand(brands_all, payload.customer_message) or brand.name
    if settings.enforce_brand_isolation and detected != brand.name:
        logger.warning("cross-brand signal detected=%s isolated_to=%s request_id=%s", detected, brand.name, request_id)
        raise HTTPException(403, "Cross-brand access detected and blocked")

    # 2) conversation + customer message
    conv = Conversation(brand_id=brand.id, detected_brand_name=detected, status="open")
    db.add(conv)
    db.flush()
    customer_msg = Message(conversation_id=conv.id, brand_id=brand.id, role="customer",
                           content=payload.customer_message, status="sent")
    db.add(customer_msg)
    db.flush()

    # Resolve the customer (optional) for order context scoping
    customer = None
    if payload.customer_email:
        customer = db.query(Customer).filter(
            Customer.brand_id == brand.id, Customer.email == payload.customer_email.lower()).first()
        if not customer:
            customer = Customer(brand_id=brand.id, email=payload.customer_email.lower())
            db.add(customer)
            db.flush()

    # 3) order lookup — THIS customer's order only (no cross-customer leakage)
    order_ctx = None
    if customer:
        order = (db.query(Order).filter(Order.brand_id == brand.id,
                                        Order.customer_id == customer.id)
                 .order_by(Order.ordered_at.desc()).first())
        if order:
            order_ctx = order.to_dict()

    # 4) build the workflow state
    state = WorkflowState(
        conversation_id=conv.id,
        brand_id=brand.id,
        brand_name=brand.name,
        customer_message=payload.customer_message,
        customer_name=customer.name if customer else "",
        customer_email=customer.email if customer else "",
        order_context=order_ctx,
        current_user_id=str(current_user.id),
        website_url=brand.website_url or "",
    )

    # 5) run the stateful pipeline
    state = await run_cx_workflow(state)
    ctx_sources = [g.chunk.to_dict() | {"passed": g.passed, "reason": g.grader_reason}
                   for g in state.graded_chunks]

    # 6) map workflow outcome to the human-review/auto-send gate
    auto_ok = state.final_status in ("approved", "greeting", "deflected")
    if auto_ok:
        code = ValidationCode.OK
        status = "approved"
        final_text = state.final_response or ""
        conv.status = "pending_send"
    else:
        reason = next((e for e in state.errors if e.startswith("escalation reason")), "")
        code = ValidationCode.NO_CONTEXT if "no_relevant_knowledge" in reason else ValidationCode.UNGROUNDED
        status = "pending_review"
        final_text = ""

    ai_draft = Message(
        conversation_id=conv.id, brand_id=brand.id, role="agent",
        content="", draft_text=state.final_response or state.generated_response or "",
        final_text=final_text,
        status=status, confidence=state.confidence_score,
        validation_code=code.value,
        context_sources=json.dumps(ctx_sources or []),
        citation=", ".join(state.citations[:3]),
    )
    db.add(ai_draft)
    db.commit()

    # 7) audit + telemetry (full audit trail incl. the exact prompt)
    db.add(AILog(
        request_id=request_id, brand_id=brand.id, conversation_id=conv.id,
        provider=last_provider(),
        customer_message=payload.customer_message,
        retrieved_chunks=json.dumps(ctx_sources or []),
        llm_response=state.generated_response or "",
        final_response=state.final_response or "",
        prompt_text=state.prompt_text,
        confidence=state.confidence_score,
        status="generated",
        node_history=json.dumps(state.node_history or []),
        grading_results=json.dumps(ctx_sources or []),
        correction_attempts=state.correction_attempts,
        escalation_reason=next((e for e in state.errors if e.startswith("escalation reason")), ""),
        scraped_content_used=state.scrape_used,
        validation_status=state.final_status,
        confidence_score=state.confidence_score,
    ))
    db.commit()

    return {
        "mode": "auto" if auto_ok else "human_review",
        "conversation": conv.to_dict(),
        "message": ai_draft.to_dict(),
        "validation": {"ok": auto_ok, "code": code.value,
                       "confidence": state.confidence_score,
                       "reason": None if auto_ok else next((e for e in state.errors if e.startswith("escalation reason")), "routed to human review")},
        "workflow": {
            "node_history": state.node_history,
            "scrape_used": state.scrape_used,
            "correction_attempts": state.correction_attempts,
            "graded": ctx_sources,
        },
    }