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

    model_config = {"from_attributes": True}


class InvoiceStatusUpdate(BaseModel):
    status: str  # draft, sent, paid, overdue
    sent_date: date | None = None
