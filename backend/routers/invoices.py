"""Endpoints for invoice preview, generation, listing, download, and import."""

import logging
import shutil
from datetime import datetime, UTC
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models.generated_invoice import GeneratedInvoice, GeneratedInvoiceItem
from backend.models.invoice_line_item_source import InvoiceLineItemSource
from backend.schemas.generated_invoice import (
    GeneratedInvoiceListResponse,
    GeneratedInvoiceResponse,
    InvoiceGenerateRequest,
    InvoicePreviewRequest,
    InvoicePreviewResponse,
    InvoiceRegenerateRequest,
    InvoiceStatusUpdate,
)
from backend.schemas.invoice_import import (
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportParsedInvoice,
    ImportParsedLineItem,
    ImportParseResponse,
)
from backend.services.invoice_engine import (
    generate_invoice,
    preview_invoice,
    regenerate_invoice,
)

logger = logging.getLogger(__name__)

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
    """Dry-run: resolve all line item amounts without generating anything.

    Uses running-balance approach — shows un-invoiced provider costs with
    contributing invoice details.
    """
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
                "contributing_invoices": [
                    {
                        "provider_invoice_id": c.provider_invoice_id,
                        "invoice_number": c.invoice_number,
                        "amount_eur": c.amount_eur,
                        "assigned_month": c.assigned_month,
                        "is_from_different_month": c.is_from_different_month,
                    }
                    for c in item.contributing_invoices
                ],
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
            excluded_provider_invoice_ids=data.excluded_provider_invoice_ids,
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


# ── Import endpoints ─────────────────────────────────────────────────


@router.post("/import/parse", response_model=ImportParseResponse)
async def parse_import_files(
    files: list[UploadFile],
    db: Session = Depends(get_db),
):
    """Upload .docx/.pdf files and extract invoice data for review.

    Files are saved to data/imports/invoices/ and parsed. Returns extracted
    data for each file with line items matched to existing definitions.
    """
    from backend.services.docx_extraction import (
        extract_client_invoice_docx,
        extract_client_invoice_pdf,
    )
    from backend.services.import_matching import (
        auto_link_to_provider_invoices,
        match_line_items_to_definitions,
    )

    imports_dir = settings.IMPORTS_DIR / "invoices"
    imports_dir.mkdir(parents=True, exist_ok=True)

    parsed_invoices: list[ImportParsedInvoice] = []
    total = len(files)

    for file in files:
        if not file.filename:
            continue

        ext = Path(file.filename).suffix.lower()
        if ext not in (".docx", ".pdf"):
            continue

        # Save file to disk
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        stored_name = f"{timestamp}_{file.filename}"
        stored_path = imports_dir / stored_name
        with open(stored_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Parse based on file type
        if ext == ".docx":
            data = extract_client_invoice_docx(str(stored_path))
        else:
            data = extract_client_invoice_pdf(str(stored_path))

        # Match line items to definitions (use first active client)
        from backend.models.client import Client

        client = db.query(Client).filter(Client.active.is_(True)).first()
        client_id = client.id if client else ""

        matched_items = match_line_items_to_definitions(
            data.line_items, client_id, db
        )

        # Auto-link to provider invoices if we have period info
        if data.period_start:
            matched_items = auto_link_to_provider_invoices(
                matched_items, data.period_start.year, data.period_start.month, db
            )

        # Build response
        rel_path = str(stored_path.relative_to(settings.DATA_DIR))
        parsed = ImportParsedInvoice(
            filename=file.filename,
            stored_path=rel_path,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date.isoformat() if data.invoice_date else None,
            period_start=data.period_start.isoformat() if data.period_start else None,
            period_end=data.period_end.isoformat() if data.period_end else None,
            client_name=data.client_name,
            line_items=[
                ImportParsedLineItem(
                    position=m.position,
                    description=m.description,
                    amount=m.amount,
                    matched_config_id=m.line_item_config_id,
                    matched_source_type=m.source_type,
                    matched_category_id=m.category_id,
                    match_confidence=m.match_confidence,
                    linked_provider_invoice_ids=[
                        lp.provider_invoice_id for lp in m.linked_provider_invoices
                    ],
                    linked_amounts=[
                        lp.amount_contributed for lp in m.linked_provider_invoices
                    ],
                )
                for m in matched_items
            ],
            net_total=data.net_total,
            tax_rate=data.tax_rate,
            tax_amount=data.tax_amount,
            gross_total=data.gross_total,
            confidence=data.confidence,
        )
        parsed_invoices.append(parsed)

    return ImportParseResponse(
        invoices=parsed_invoices,
        total=total,
        parsed=len(parsed_invoices),
    )


@router.post("/import/confirm", response_model=ImportConfirmResponse)
def confirm_import(
    data: ImportConfirmRequest,
    db: Session = Depends(get_db),
):
    """Save reviewed imported invoices to the database.

    Creates GeneratedInvoice records with source='imported',
    GeneratedInvoiceItem records with line_item_config_id,
    and InvoiceLineItemSource records for linked provider invoices.
    """
    created = 0
    linked_sources = 0
    errors: list[str] = []

    for inv_data in data.invoices:
        # Check for duplicate invoice number
        existing = (
            db.query(GeneratedInvoice)
            .filter(GeneratedInvoice.invoice_number == inv_data.invoice_number)
            .first()
        )
        if existing:
            errors.append(
                f"Invoice {inv_data.invoice_number} already exists (id={existing.id})"
            )
            continue

        # Derive period_year and period_month from period_start or invoice_date
        if inv_data.period_start:
            period_year = inv_data.period_start.year
            period_month = inv_data.period_start.month
        else:
            period_year = inv_data.invoice_date.year
            period_month = inv_data.invoice_date.month

        # Build the original file path (relative to DATA_DIR)
        original_file_path = inv_data.stored_path if inv_data.stored_path else None

        invoice = GeneratedInvoice(
            client_id=inv_data.client_id,
            invoice_number=inv_data.invoice_number,
            invoice_number_display=f"Rechnung {inv_data.invoice_number}",
            period_year=period_year,
            period_month=period_month,
            invoice_date=inv_data.invoice_date,
            net_total=inv_data.net_total,
            vat_amount=inv_data.vat_amount,
            gross_total=inv_data.gross_total,
            status=inv_data.status,
            source="imported",
            original_file_path=original_file_path,
            period_start=inv_data.period_start,
            period_end=inv_data.period_end,
        )
        db.add(invoice)
        db.flush()  # get invoice.id

        for li_data in inv_data.line_items:
            item = GeneratedInvoiceItem(
                invoice_id=invoice.id,
                position=li_data.position,
                label=li_data.description,
                amount=li_data.amount,
                source_type=li_data.source_type or "manual",
                category_id=li_data.category_id,
                line_item_config_id=li_data.line_item_config_id,
            )
            db.add(item)
            db.flush()  # get item.id

            # Create source links for provider invoices
            for pi_id, pi_amount in zip(
                li_data.provider_invoice_ids, li_data.provider_invoice_amounts
            ):
                source = InvoiceLineItemSource(
                    line_item_id=item.id,
                    provider_invoice_id=pi_id,
                    amount_contributed=pi_amount,
                )
                db.add(source)
                linked_sources += 1

        created += 1

    db.commit()
    logger.info("Imported %d invoices with %d source links", created, linked_sources)

    return ImportConfirmResponse(
        created=created,
        linked_sources=linked_sources,
        errors=errors,
    )
