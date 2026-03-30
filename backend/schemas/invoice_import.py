"""Pydantic schemas for invoice import (parse + confirm workflow)."""

from datetime import date

from pydantic import BaseModel


# ── Parse response (extracted data for review) ──────────────────────


class ImportParsedLineItem(BaseModel):
    position: int
    description: str
    amount: float
    matched_config_id: int | None = None
    matched_source_type: str | None = None
    matched_category_id: str | None = None
    match_confidence: str = "none"
    linked_provider_invoice_ids: list[int] = []
    linked_amounts: list[float] = []


class ImportParsedInvoice(BaseModel):
    filename: str
    stored_path: str
    invoice_number: str | None = None
    invoice_date: str | None = None  # ISO format
    period_start: str | None = None
    period_end: str | None = None
    client_name: str | None = None
    line_items: list[ImportParsedLineItem] = []
    net_total: float | None = None
    tax_rate: float | None = None
    tax_amount: float | None = None
    gross_total: float | None = None
    confidence: str = "low"


class ImportParseResponse(BaseModel):
    invoices: list[ImportParsedInvoice]
    total: int
    parsed: int


# ── Confirm request (user-reviewed data to save) ────────────────────


class ImportConfirmLineItem(BaseModel):
    position: int
    description: str
    amount: float
    line_item_config_id: int | None = None
    source_type: str | None = None
    category_id: str | None = None
    provider_invoice_ids: list[int] = []
    provider_invoice_amounts: list[float] = []


class ImportConfirmInvoice(BaseModel):
    stored_path: str
    invoice_number: str
    invoice_date: date
    period_start: date | None = None
    period_end: date | None = None
    client_id: str
    status: str = "sent"
    line_items: list[ImportConfirmLineItem]
    net_total: float
    tax_rate: float = 19.0
    vat_amount: float
    gross_total: float


class ImportConfirmRequest(BaseModel):
    invoices: list[ImportConfirmInvoice]


class ImportConfirmResponse(BaseModel):
    created: int
    linked_sources: int
    errors: list[str] = []
