"""CRUD endpoints for cost categories."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.cost_category import CostCategory
from backend.schemas.cost_category import (
    CostCategoryCreate,
    CostCategoryResponse,
    CostCategoryUpdate,
)

router = APIRouter(prefix="/api/cost-categories", tags=["cost-categories"])


@router.get("", response_model=list[CostCategoryResponse])
def list_cost_categories(
    active_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(CostCategory)
    if active_only:
        query = query.filter(CostCategory.active.is_(True))
    return query.order_by(CostCategory.sort_order, CostCategory.name).offset(skip).limit(limit).all()


@router.get("/{category_id}", response_model=CostCategoryResponse)
def get_cost_category(category_id: str, db: Session = Depends(get_db)):
    cat = db.get(CostCategory, category_id)
    if not cat:
        raise HTTPException(404, f"Cost category '{category_id}' not found")
    return cat


@router.post("", response_model=CostCategoryResponse, status_code=201)
def create_cost_category(data: CostCategoryCreate, db: Session = Depends(get_db)):
    if db.get(CostCategory, data.id):
        raise HTTPException(409, f"Cost category '{data.id}' already exists")
    dump = data.model_dump()
    keywords = dump.pop("bank_keywords", [])
    cat = CostCategory(**dump)
    cat.bank_keywords = keywords
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.patch("/{category_id}", response_model=CostCategoryResponse)
def update_cost_category(
    category_id: str, data: CostCategoryUpdate, db: Session = Depends(get_db)
):
    cat = db.get(CostCategory, category_id)
    if not cat:
        raise HTTPException(404, f"Cost category '{category_id}' not found")
    updates = data.model_dump(exclude_unset=True)
    keywords = updates.pop("bank_keywords", None)
    for key, value in updates.items():
        setattr(cat, key, value)
    if keywords is not None:
        cat.bank_keywords = keywords
    db.commit()
    db.refresh(cat)
    return cat
