"""Pydantic schemas for GeneratedInvoice and GeneratedInvoiceItem."""

from datetime import date, datetime

from pydantic import BaseModel


class GeneratedInvoiceItemResponse(BaseModel):
    id: int
    invoice_id: int
    position: int
    label: str
    amount: float
    source_type: str
    category_id: str | None = None
    provider_invoice_id: int | None = None
    distribution_source_id: int | None = None
    distribution_months_json: str | None = None
    upwork_tx_ids_json: str | None = None
    notes: str | None = None
    line_item_config_id: int | None = None

    model_config = {"from_attributes": True}


class GeneratedInvoiceResponse(BaseModel):
    id: int
    client_id: str
    invoice_number: str
    invoice_number_display: str | None = None
    filename: str | None = None
    period_year: int
    period_month: int
    invoice_date: date
    net_total: float
    vat_amount: float
    gross_total: float
    status: str
    file_path: str | None = None
    pdf_path: str | None = None
    sent_date: date | None = None
    created_at: datetime
    notes: str | None = None
    source: str = "generated"
    original_file_path: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    items: list[GeneratedInvoiceItemResponse] = []

    model_config = {"from_attributes": True}


class GeneratedInvoiceListResponse(BaseModel):
    id: int
    client_id: str
    invoice_number: str
    period_year: int
    period_month: int
    invoice_date: date
    net_total: float
    vat_amount: float
    gross_total: float
    status: str
    created_at: datetime
    source: str = "generated"

    model_config = {"from_attributes": True}


class InvoiceStatusUpdate(BaseModel):
    status: str  # draft, sent, paid, overdue
    sent_date: date | None = None


# ── Preview & Generation schemas ──────────────────────────────────


class InvoicePreviewRequest(BaseModel):
    client_id: str
    year: int
    month: int


class ContributingInvoiceResponse(BaseModel):
    provider_invoice_id: int
    invoice_number: str
    amount_eur: float
    assigned_month: str | None = None
    is_from_different_month: bool = False


class ResolvedLineItemResponse(BaseModel):
    position: int
    label: str
    amount: float
    source_type: str
    category_id: str | None = None
    provider_invoice_id: int | None = None
    distribution_source_id: int | None = None
    distribution_months: list[str] | None = None
    upwork_tx_ids: list[str] | None = None
    warnings: list[str] = []
    contributing_invoices: list[ContributingInvoiceResponse] = []


class InvoicePreviewResponse(BaseModel):
    client_id: str
    year: int
    month: int
    items: list[ResolvedLineItemResponse]
    net_total: float
    vat_amount: float
    gross_total: float
    warnings: list[str] = []


class InvoiceGenerateRequest(BaseModel):
    client_id: str
    year: int
    month: int
    invoice_number: str
    invoice_date: date
    overrides: dict[int, float] | None = None
    notes: str | None = None
    excluded_provider_invoice_ids: list[int] | None = None


class InvoiceRegenerateRequest(BaseModel):
    overrides: dict[int, float] | None = None
    notes: str | None = None
