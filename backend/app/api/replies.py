"""Reply log / history for a brand (agent messages), exercised by admin + audit view.
Reads are scoped: agents only see their own brand's replies. Each entry is
decorated with the originating customer message for a complete audit trail."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import can_access_brand, require_agent, scoped_brand_id
from app.db.session import get_db
from app.models.brand import Brand
from app.models.message import Message
from app.models.user import User

router = APIRouter()


@router.get("")
def list_replies(brand_id: str | None = None, db: Session = Depends(get_db),
                 current_user: User = Depends(require_agent)):
    q = db.query(Message).filter(Message.role == "agent")
    scoped = scoped_brand_id(current_user)
    if brand_id:
        if scoped and scoped != brand_id:
            raise HTTPException(403, "You do not have access to this brand")
        q = q.filter(Message.brand_id == brand_id)
    elif scoped:
        q = q.filter(Message.brand_id == scoped)
    rows = q.order_by(Message.created_at.desc()).limit(200).all()
    out = []
    for m in rows:
        brand = db.get(Brand, m.brand_id)
        d = m.to_dict()
        d["brand_name"] = brand.name if brand else ""
        cust = (db.query(Message).filter(Message.conversation_id == m.conversation_id,
                                         Message.role == "customer")
                .order_by(Message.created_at).first())
        d["customer_message"] = cust.content if cust else ""
        out.append(d)
    return out


@router.get("/{message_id}")
def get_reply(message_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_agent)):
    m = db.get(Message, message_id)
    if not m:
        raise HTTPException(404, "Message not found")
    if not can_access_brand(current_user, m.brand_id):
        raise HTTPException(403, "You do not have access to this brand")
    brand = db.get(Brand, m.brand_id)
    d = m.to_dict()
    d["brand_name"] = brand.name if brand else ""
    return d