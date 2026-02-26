"""Provider invoice service — CRUD + PDF file storage.

Manages provider invoices and their associated PDF files, stored under
``data/categories/{category_id}/``.
"""

import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.provider_invoice import ProviderInvoice


def _category_dir(category_id: str) -> Path:
    """Return the storage directory for a category's files."""
    return settings.CATEGORIES_DIR / category_id


def store_provider_invoice_pdf(
    category_id: str,
    filename: str,
    source_path: str,
) -> str:
    """Copy a provider invoice PDF to the category's storage directory.

    Returns the relative file path (relative to DATA_DIR) for storage in DB.
    """
    dest_dir = _category_dir(category_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    shutil.copy2(source_path, dest)
    return str(dest.relative_to(settings.DATA_DIR))


def get_provider_invoice_path(invoice: ProviderInvoice) -> Path | None:
    """Return the absolute path to a provider invoice's PDF, or None."""
    if not invoice.file_path:
        return None
    full_path = settings.DATA_DIR / invoice.file_path
    if full_path.exists():
        return full_path
    return None


def list_provider_invoices(
    db: Session,
    category_id: str | None = None,
    assigned_month: str | None = None,
) -> list[ProviderInvoice]:
    """List provider invoices with optional filters."""
    query = db.query(ProviderInvoice)
    if category_id:
        query = query.filter(ProviderInvoice.category_id == category_id)
    if assigned_month:
        query = query.filter(ProviderInvoice.assigned_month == assigned_month)
    return query.order_by(ProviderInvoice.invoice_date.desc()).all()
