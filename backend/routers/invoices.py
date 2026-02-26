"""Endpoints for generated invoices (list, get, status update).

Invoice generation (preview + create) is Phase 4. This router provides
read access and status management for already-generated invoices.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.generated_invoice import GeneratedInvoice
from backend.schemas.generated_invoice import (
    GeneratedInvoiceListResponse,
    GeneratedInvoiceResponse,
    InvoiceStatusUpdate,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=list[GeneratedInvoiceListResponse])
def list_invoices(
    client_id: str | None = None,
    status: str | None = None,
    year: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(GeneratedInvoice)
    if client_id:
        query = query.filter(GeneratedInvoice.client_id == client_id)
    if status:
        query = query.filter(GeneratedInvoice.status == status)
    if year:
        query = query.filter(GeneratedInvoice.period_year == year)
    return query.order_by(
        GeneratedInvoice.period_year.desc(), GeneratedInvoice.period_month.desc()
    ).all()


@router.get("/{invoice_id}", response_model=GeneratedInvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(GeneratedInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    return inv


@router.patch("/{invoice_id}/status", response_model=GeneratedInvoiceResponse)
def update_invoice_status(
    invoice_id: int, data: InvoiceStatusUpdate, db: Session = Depends(get_db)
):
    inv = db.get(GeneratedInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")

    valid_statuses = {"draft", "sent", "paid", "overdue"}
    if data.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    inv.status = data.status
    if data.sent_date:
        inv.sent_date = data.sent_date
    db.commit()
    db.refresh(inv)
    return inv
