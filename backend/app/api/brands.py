"""Brand CRUD — the CORE of the manual admin flow.

Manual brand CRUD is core; crawling is optional (handled by the workflow's
internal SSRF-safe scraper or /api/knowledge/crawl for admins). Reads pass
through per-user brand scoping so document embeddings are never exposed across
brands. Writes are admin-only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import can_access_brand, require_admin, require_agent, scoped_brand_id
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.brand import Brand
from app.models.user import User
from app.schemas.schemas import BrandCreate, BrandOut, BrandUpdate
from app.services.brand_detect import detect_brand
from app.services.vector_store import delete_all_for_brand

router = APIRouter()


@router.get("", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db), current_user: User = Depends(require_agent)):
    q = db.query(Brand)
    if scoped := scoped_brand_id(current_user):
        q = q.filter(Brand.id == scoped)
    return q.order_by(Brand.name).all()


@router.post("", response_model=BrandOut, status_code=201)
def create_brand(payload: BrandCreate, db: Session = Depends(get_db),
                 current_user: User = Depends(require_admin)):
    existing = db.query(Brand).filter(Brand.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(409, "A brand with this name already exists")
    brand = Brand(
        name=payload.name.strip(),
        description=payload.description,
        website_url=payload.website_url,
    )
    db.add(brand)
    db.add(AuditLog(actor_user_id=current_user.id, entity_type="brand", action="create", detail=brand.name))
    db.commit()
    db.refresh(brand)
    return brand


@router.get("/detect", response_model=dict)
def detect(query: str, db: Session = Depends(get_db), current_user: User = Depends(require_agent)):
    brands = [b.name for b in db.query(Brand).all()]
    return {"brand": detect_brand(brands, query)}


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(brand_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_agent)):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    if not can_access_brand(current_user, brand.id):
        raise HTTPException(403, "You do not have access to this brand")
    return brand


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: str, payload: BrandUpdate, db: Session = Depends(get_db),
                 current_user: User = Depends(require_admin)):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        clash = db.query(Brand).filter(Brand.name == data["name"].strip(), Brand.id != brand_id).first()
        if clash:
            raise HTTPException(409, "A brand with this name already exists")
        data["name"] = data["name"].strip()
    for k, v in data.items():
        setattr(brand, k, v)
    db.add(AuditLog(actor_user_id=current_user.id, entity_type="brand", entity_id=brand.id,
                    action="update", detail=brand.name))
    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/{brand_id}", status_code=204)
def delete_brand(brand_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")
    delete_all_for_brand(brand.name)
    db.add(AuditLog(actor_user_id=current_user.id, entity_type="brand", entity_id=brand.id,
                    action="delete", detail=brand.name))
    db.delete(brand)
    db.commit()
    return None