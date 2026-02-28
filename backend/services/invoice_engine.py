"""Invoice engine — preview and generate orchestrator.

``preview_invoice`` resolves amounts and returns a dry-run preview.
``generate_invoice`` renders HTML/PDF, persists the invoice record, and
links source transactions for traceability.
"""

import json
import logging
import shutil
from datetime import date, datetime, UTC
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.client import Client
from backend.models.company_settings import CompanySettings
from backend.models.generated_invoice import GeneratedInvoice, GeneratedInvoiceItem
from backend.services.cost_calculation import InvoicePreview, resolve_line_items
from backend.services.formatting import (
    format_date_german,
    format_period,
    invoice_filename,
)
from backend.services.invoice_renderer import render_and_save_pdf, render_invoice_html


def preview_invoice(
    client_id: str,
    year: int,
    month: int,
    db: Session,
) -> InvoicePreview:
    """Dry-run: resolve all line item amounts for a client/month.

    Returns an InvoicePreview with items, totals, and warnings.
    No data is written.
    """
    return resolve_line_items(client_id, year, month, db)


def generate_invoice(
    *,
    client_id: str,
    year: int,
    month: int,
    invoice_number: str,
    invoice_date: date,
    overrides: dict[int, float] | None = None,
    notes: str | None = None,
    db: Session,
) -> GeneratedInvoice:
    """Full generation workflow: resolve, render, store.

    Args:
        client_id: Client PK (e.g. ``"drs"``).
        year, month: Billing period.
        invoice_number: User-confirmed invoice number (e.g. ``"202501-02"``).
        invoice_date: Invoice date shown on the document.
        overrides: Optional dict mapping position -> amount to override resolved values.
        notes: Optional notes stored with the invoice.
        db: SQLAlchemy session.

    Returns:
        The persisted ``GeneratedInvoice`` record.

    Raises:
        ValueError: If the client doesn't exist or the invoice number is already taken.
    """
    # 1. Validate client
    client = db.get(Client, client_id)
    if not client:
        raise ValueError(f"Client '{client_id}' not found")

    # Check for duplicate invoice number
    existing = (
        db.query(GeneratedInvoice)
        .filter(GeneratedInvoice.invoice_number == invoice_number)
        .first()
    )
    if existing:
        raise ValueError(
            f"Invoice number '{invoice_number}' already exists (id={existing.id})"
        )

    # 2. Resolve line items
    preview = resolve_line_items(client_id, year, month, db)

    # 3. Apply overrides
    if overrides:
        for item in preview.items:
            if item.position in overrides:
                item.amount = overrides[item.position]
                if item.source_type != "manual":
                    item.source_type = "manual"

        # Recalculate totals
        net = sum(Decimal(str(item.amount)) for item in preview.items)
        net_rounded = net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        vat = (net_rounded * Decimal(str(client.vat_rate))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        gross = net_rounded + vat
        preview.net_total = float(net_rounded)
        preview.vat_amount = float(vat)
        preview.gross_total = float(gross)

    # 4. Load company settings
    company = db.get(CompanySettings, 1)
    if not company:
        company = CompanySettings(id=1)
        db.add(company)
        db.flush()

    # 5. Render HTML
    items_for_render = [
        {"position": item.position, "label": item.label, "amount": item.amount}
        for item in preview.items
    ]

    html = render_invoice_html(
        client_name=client.name,
        client_address_line1=client.address_line1,
        client_zip_city=client.zip_city,
        client_address_line2=client.address_line2,
        invoice_number=invoice_number,
        invoice_date_str=format_date_german(invoice_date),
        period_str=format_period(year, month),
        items=items_for_render,
        net_total=preview.net_total,
        vat_amount=preview.vat_amount,
        gross_total=preview.gross_total,
        company=company,
    )

    # 6. Render PDF
    fname = invoice_filename(year, month, client.client_number)
    year_dir = settings.GENERATED_DIR / str(year)
    pdf_path = year_dir / fname
    render_and_save_pdf(html, pdf_path)

    # Relative path for DB storage
    relative_pdf_path = f"generated/{year}/{fname}"

    # 7. Persist invoice record
    invoice = GeneratedInvoice(
        client_id=client_id,
        invoice_number=invoice_number,
        invoice_number_display=f"Rechnung {invoice_number}",
        filename=fname,
        period_year=year,
        period_month=month,
        invoice_date=invoice_date,
        net_total=preview.net_total,
        vat_amount=preview.vat_amount,
        gross_total=preview.gross_total,
        status="draft",
        pdf_path=relative_pdf_path,
        notes=notes,
    )
    db.add(invoice)
    db.flush()  # get the id

    # 8. Persist line items with traceability links
    for item in preview.items:
        inv_item = GeneratedInvoiceItem(
            invoice_id=invoice.id,
            position=item.position,
            label=item.label,
            amount=item.amount,
            source_type=item.source_type,
            category_id=item.category_id,
            provider_invoice_id=item.provider_invoice_id,
            distribution_source_id=item.distribution_source_id,
            distribution_months_json=(
                json.dumps(item.distribution_months) if item.distribution_months else None
            ),
            upwork_tx_ids_json=(
                json.dumps(item.upwork_tx_ids) if item.upwork_tx_ids else None
            ),
        )
        db.add(inv_item)

    db.commit()
    db.refresh(invoice)
    logger.info(
        "Generated invoice %s for %s/%02d: net=%.2f, gross=%.2f, pdf=%s",
        invoice_number, year, month, preview.net_total, preview.gross_total, relative_pdf_path,
    )
    return invoice


def regenerate_invoice(
    invoice_id: int,
    *,
    overrides: dict[int, float] | None = None,
    notes: str | None = None,
    db: Session,
) -> GeneratedInvoice:
    """Re-generate an existing invoice: archive old PDF, delete record, generate fresh.

    The original invoice_number, invoice_date, client_id, and period are preserved.
    Overrides and notes can be updated.

    Raises:
        ValueError: If the invoice doesn't exist.
    """
    old = db.get(GeneratedInvoice, invoice_id)
    if not old:
        raise ValueError(f"Invoice id={invoice_id} not found")

    # Capture params from old invoice
    client_id = old.client_id
    year = old.period_year
    month = old.period_month
    inv_number = old.invoice_number
    inv_date = old.invoice_date
    old_notes = old.notes

    # Archive old PDF if it exists on disk
    if old.pdf_path:
        old_pdf = settings.DATA_DIR / old.pdf_path
        if old_pdf.exists():
            archive_dir = settings.GENERATED_DIR / str(year) / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
            archive_name = f"{old_pdf.stem}_{ts}{old_pdf.suffix}"
            shutil.move(str(old_pdf), str(archive_dir / archive_name))

    # Delete old record (cascade deletes items)
    db.delete(old)
    db.flush()

    logger.info("Regenerating invoice id=%d (%s)", invoice_id, inv_number)

    # Generate fresh invoice with same params
    return generate_invoice(
        client_id=client_id,
        year=year,
        month=month,
        invoice_number=inv_number,
        invoice_date=inv_date,
        overrides=overrides,
        notes=notes if notes is not None else old_notes,
        db=db,
    )
