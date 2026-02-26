"""CRUD endpoints for provider invoices (+ PDF upload/download)."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.provider_invoice import ProviderInvoice
from backend.schemas.provider_invoice import (
    ProviderInvoiceCreate,
    ProviderInvoiceResponse,
    ProviderInvoiceUpdate,
)
from backend.services.provider_invoice_service import get_provider_invoice_path

router = APIRouter(prefix="/api/provider-invoices", tags=["provider-invoices"])


@router.get("", response_model=list[ProviderInvoiceResponse])
def list_provider_invoices(
    category_id: str | None = None,
    assigned_month: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(ProviderInvoice)
    if category_id:
        query = query.filter(ProviderInvoice.category_id == category_id)
    if assigned_month:
        query = query.filter(ProviderInvoice.assigned_month == assigned_month)
    return query.order_by(ProviderInvoice.invoice_date.desc()).all()


@router.get("/{invoice_id}", response_model=ProviderInvoiceResponse)
def get_provider_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(ProviderInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Provider invoice {invoice_id} not found")
    return inv


@router.post("", response_model=ProviderInvoiceResponse, status_code=201)
def create_provider_invoice(
    data: ProviderInvoiceCreate, db: Session = Depends(get_db)
):
    dump = data.model_dump()
    covers = dump.pop("covers_months", [])
    inv = ProviderInvoice(**dump)
    inv.covers_months = covers
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.patch("/{invoice_id}", response_model=ProviderInvoiceResponse)
def update_provider_invoice(
    invoice_id: int, data: ProviderInvoiceUpdate, db: Session = Depends(get_db)
):
    inv = db.get(ProviderInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Provider invoice {invoice_id} not found")
    updates = data.model_dump(exclude_unset=True)
    covers = updates.pop("covers_months", None)
    for key, value in updates.items():
        setattr(inv, key, value)
    if covers is not None:
        inv.covers_months = covers
    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{invoice_id}", status_code=204)
def delete_provider_invoice(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(ProviderInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Provider invoice {invoice_id} not found")
    db.delete(inv)
    db.commit()


@router.post("/{invoice_id}/upload", response_model=ProviderInvoiceResponse)
def upload_provider_invoice_pdf(
    invoice_id: int, file: UploadFile, db: Session = Depends(get_db)
):
    inv = db.get(ProviderInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Provider invoice {invoice_id} not found")

    # Store file in category directory
    dest_dir = settings.CATEGORIES_DIR / inv.category_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (file.filename or f"{inv.invoice_number}.pdf")

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    inv.file_path = str(dest.relative_to(settings.DATA_DIR))
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/{invoice_id}/download")
def download_provider_invoice_pdf(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(ProviderInvoice, invoice_id)
    if not inv:
        raise HTTPException(404, f"Provider invoice {invoice_id} not found")

    path = get_provider_invoice_path(inv)
    if not path:
        raise HTTPException(404, "PDF file not found")

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
    )
