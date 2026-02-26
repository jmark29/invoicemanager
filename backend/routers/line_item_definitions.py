"""CRUD endpoints for line item definitions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.line_item_definition import LineItemDefinition
from backend.schemas.line_item_definition import (
    LineItemDefinitionCreate,
    LineItemDefinitionResponse,
    LineItemDefinitionUpdate,
)

router = APIRouter(prefix="/api/line-item-definitions", tags=["line-item-definitions"])


@router.get("", response_model=list[LineItemDefinitionResponse])
def list_line_item_definitions(
    client_id: str | None = None, db: Session = Depends(get_db)
):
    query = db.query(LineItemDefinition)
    if client_id:
        query = query.filter(LineItemDefinition.client_id == client_id)
    return query.order_by(LineItemDefinition.sort_order, LineItemDefinition.position).all()


@router.get("/{definition_id}", response_model=LineItemDefinitionResponse)
def get_line_item_definition(definition_id: int, db: Session = Depends(get_db)):
    defn = db.get(LineItemDefinition, definition_id)
    if not defn:
        raise HTTPException(404, f"Line item definition {definition_id} not found")
    return defn


@router.post("", response_model=LineItemDefinitionResponse, status_code=201)
def create_line_item_definition(
    data: LineItemDefinitionCreate, db: Session = Depends(get_db)
):
    defn = LineItemDefinition(**data.model_dump())
    db.add(defn)
    db.commit()
    db.refresh(defn)
    return defn


@router.patch("/{definition_id}", response_model=LineItemDefinitionResponse)
def update_line_item_definition(
    definition_id: int, data: LineItemDefinitionUpdate, db: Session = Depends(get_db)
):
    defn = db.get(LineItemDefinition, definition_id)
    if not defn:
        raise HTTPException(404, f"Line item definition {definition_id} not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(defn, key, value)
    db.commit()
    db.refresh(defn)
    return defn


@router.delete("/{definition_id}", status_code=204)
def delete_line_item_definition(definition_id: int, db: Session = Depends(get_db)):
    defn = db.get(LineItemDefinition, definition_id)
    if not defn:
        raise HTTPException(404, f"Line item definition {definition_id} not found")
    db.delete(defn)
    db.commit()
