"""Endpoints for invoice preview, generation, listing, and download."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.generated_invoice import GeneratedInvoice
from backend.schemas.generated_invoice import (
    GeneratedInvoiceListResponse,
    GeneratedInvoiceResponse,
    InvoiceGenerateRequest,
    InvoicePreviewRequest,
    InvoicePreviewResponse,
    InvoiceRegenerateRequest,
    InvoiceStatusUpdate,
)
from backend.services.invoice_engine import (
    generate_invoice,
    preview_invoice,
    regenerate_invoice,
)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.get("", response_model=list[GeneratedInvoiceListResponse])
def list_invoices(
    client_id: str | None = None,
    status: str | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 100,
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
    ).offset(skip).limit(limit).all()


@router.get("/{invoice_id}", response_model=GeneratedInvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(GeneratedInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    return inv


@router.post("/preview", response_model=InvoicePreviewResponse)
def preview(data: InvoicePreviewRequest, db: Session = Depends(get_db)):
    """Dry-run: resolve all line item amounts without generating anything."""
    result = preview_invoice(data.client_id, data.year, data.month, db)
    return InvoicePreviewResponse(
        client_id=result.client_id,
        year=result.year,
        month=result.month,
        items=[
            {
                "position": item.position,
                "label": item.label,
                "amount": item.amount,
                "source_type": item.source_type,
                "category_id": item.category_id,
                "provider_invoice_id": item.provider_invoice_id,
                "distribution_source_id": item.distribution_source_id,
                "distribution_months": item.distribution_months,
                "upwork_tx_ids": item.upwork_tx_ids,
                "warnings": item.warnings,
            }
            for item in result.items
        ],
        net_total=result.net_total,
        vat_amount=result.vat_amount,
        gross_total=result.gross_total,
        warnings=result.warnings,
    )


@router.post("", response_model=GeneratedInvoiceResponse, status_code=201)
def create_invoice(data: InvoiceGenerateRequest, db: Session = Depends(get_db)):
    """Generate an invoice: resolve amounts, render HTML/PDF, persist record."""
    try:
        invoice = generate_invoice(
            client_id=data.client_id,
            year=data.year,
            month=data.month,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            overrides=data.overrides,
            notes=data.notes,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return invoice


@router.get("/{invoice_id}/download")
def download_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Download the generated PDF for an invoice."""
    inv = db.get(GeneratedInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    if not inv.pdf_path:
        raise HTTPException(404, "No PDF file for this invoice")

    pdf_full_path = settings.DATA_DIR / inv.pdf_path
    if not pdf_full_path.exists():
        raise HTTPException(404, f"PDF file not found on disk: {inv.pdf_path}")

    return FileResponse(
        path=str(pdf_full_path),
        media_type="application/pdf",
        filename=inv.filename or f"{inv.invoice_number}.pdf",
    )


@router.post("/{invoice_id}/regenerate", response_model=GeneratedInvoiceResponse)
def regenerate(
    invoice_id: int, data: InvoiceRegenerateRequest, db: Session = Depends(get_db)
):
    """Re-generate an invoice: archive old PDF, delete record, generate fresh."""
    try:
        invoice = regenerate_invoice(
            invoice_id, overrides=data.overrides, notes=data.notes, db=db
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return invoice


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
