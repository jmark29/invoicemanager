"""Pydantic schemas for bulk PDF upload and confirmation."""

from datetime import date

from pydantic import BaseModel


class BulkUploadExtraction(BaseModel):
    """Metadata extracted from a single uploaded PDF (returned to frontend for review)."""
    filename: str
    stored_path: str  # relative to DATA_DIR
    invoice_number: str | None = None
    invoice_date: date | None = None
    amount: float | None = None
    currency: str | None = None
    category_id: str | None = None
    confidence: str = "low"  # high, medium, low


class BulkUploadResponse(BaseModel):
    """Response from the bulk-upload endpoint."""
    extractions: list[BulkUploadExtraction]
    total: int
    extracted: int  # how many had at least one field extracted


class BulkUploadConfirmItem(BaseModel):
    """A single item to confirm (user-reviewed, possibly edited)."""
    filename: str
    stored_path: str
    invoice_number: str
    invoice_date: date
    amount: float
    currency: str = "EUR"
    category_id: str
    assigned_month: str | None = None  # defaults to invoice_date month


class BulkUploadConfirmRequest(BaseModel):
    """Request body for bulk-confirm endpoint."""
    items: list[BulkUploadConfirmItem]


class BulkUploadConfirmResponse(BaseModel):
    """Response from the bulk-confirm endpoint."""
    created: int
    auto_matched: int
    errors: list[str]
