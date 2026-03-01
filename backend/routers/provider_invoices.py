"""CRUD endpoints for provider invoices (+ PDF upload/download + bulk upload)."""

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.cost_category import CostCategory
from backend.models.provider_invoice import ProviderInvoice
from backend.schemas.bulk_upload import (
    BulkUploadConfirmRequest,
    BulkUploadConfirmResponse,
    BulkUploadResponse,
)
from backend.schemas.provider_invoice import (
    ProviderInvoiceCreate,
    ProviderInvoiceResponse,
    ProviderInvoiceUpdate,
)
from backend.services.file_validation import validate_pdf
from backend.services.provider_invoice_service import get_provider_invoice_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/provider-invoices", tags=["provider-invoices"])


@router.get("", response_model=list[ProviderInvoiceResponse])
def list_provider_invoices(
    category_id: str | None = None,
    assigned_month: str | None = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    query = db.query(ProviderInvoice)
    if category_id:
        query = query.filter(ProviderInvoice.category_id == category_id)
    if assigned_month:
        query = query.filter(ProviderInvoice.assigned_month == assigned_month)
    return query.order_by(ProviderInvoice.invoice_date.desc()).offset(skip).limit(limit).all()


@router.post("/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_pdfs(
    files: list[UploadFile],
    category_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Upload multiple PDFs and extract metadata for review.

    Accepts multipart file uploads. Returns extracted metadata for each file
    so the user can review/edit before confirming.
    """
    from backend.schemas.bulk_upload import BulkUploadExtraction
    from backend.services.pdf_extraction import extract_invoice_data

    categories = db.query(CostCategory).all()

    extractions: list[BulkUploadExtraction] = []
    extracted_count = 0

    for file in files:
        validate_pdf(file)

        # Save to a temp file for pdfplumber, then move to inbox/category dir
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        data = extract_invoice_data(
            pdf_path=tmp_path,
            filename=file.filename or "unknown.pdf",
            categories=categories,
            preset_category_id=category_id,
        )

        # Move file to permanent storage
        final_category = data.category_id or "inbox"
        dest_dir = settings.CATEGORIES_DIR / final_category
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / (file.filename or "unknown.pdf")

        # Avoid overwriting existing files
        if dest.exists():
            stem = dest.stem
            suffix = dest.suffix
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.move(tmp_path, str(dest))
        rel_path = str(dest.relative_to(settings.DATA_DIR))

        has_data = any([data.invoice_number, data.invoice_date, data.amount])
        if has_data:
            extracted_count += 1

        extractions.append(BulkUploadExtraction(
            filename=file.filename or "unknown.pdf",
            stored_path=rel_path,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            amount=data.amount,
            currency=data.currency,
            category_id=data.category_id,
            confidence=data.confidence,
        ))

    return BulkUploadResponse(
        extractions=extractions,
        total=len(files),
        extracted=extracted_count,
    )


@router.post("/bulk-confirm", response_model=BulkUploadConfirmResponse)
def bulk_confirm(
    data: BulkUploadConfirmRequest,
    db: Session = Depends(get_db),
):
    """Create provider invoice records from reviewed bulk upload data.

    Expects the user-reviewed (possibly edited) extraction data.
    Creates records and triggers auto-matching for each.
    """
    from backend.services.transaction_matching import auto_match_after_invoice_creation

    created = 0
    auto_matched = 0
    errors: list[str] = []

    for item in data.items:
        try:
            # Determine assigned_month from invoice_date if not set
            assigned_month = item.assigned_month
            if not assigned_month:
                assigned_month = item.invoice_date.strftime("%Y-%m")

            # Move file from inbox to category dir if needed
            stored_path = item.stored_path
            current_full = settings.DATA_DIR / stored_path
            expected_dir = settings.CATEGORIES_DIR / item.category_id
            if current_full.exists() and current_full.parent != expected_dir:
                expected_dir.mkdir(parents=True, exist_ok=True)
                new_dest = expected_dir / current_full.name
                if new_dest.exists():
                    stem = new_dest.stem
                    suffix = new_dest.suffix
                    counter = 1
                    while new_dest.exists():
                        new_dest = expected_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                shutil.move(str(current_full), str(new_dest))
                stored_path = str(new_dest.relative_to(settings.DATA_DIR))

            inv = ProviderInvoice(
                category_id=item.category_id,
                invoice_number=item.invoice_number,
                invoice_date=item.invoice_date,
                amount=item.amount,
                currency=item.currency,
                assigned_month=assigned_month,
                file_path=stored_path,
            )
            db.add(inv)
            db.commit()
            db.refresh(inv)

            # Try auto-matching
            match = auto_match_after_invoice_creation(inv.id, db)
            if match and match.confidence >= 0.95:
                auto_matched += 1

            created += 1
        except Exception as e:
            db.rollback()
            errors.append(f"{item.filename}: {e}")
            logger.warning("Bulk confirm error for %s: %s", item.filename, e)

    return BulkUploadConfirmResponse(
        created=created,
        auto_matched=auto_matched,
        errors=errors,
    )


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

    # Auto-match against existing unlinked bank transactions
    from backend.services.transaction_matching import auto_match_after_invoice_creation
    auto_match_after_invoice_creation(inv.id, db)
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
    validate_pdf(file)

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
