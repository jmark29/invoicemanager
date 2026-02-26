"""Pydantic schemas for ProviderInvoice."""

from datetime import date, datetime

from pydantic import BaseModel


class ProviderInvoiceBase(BaseModel):
    category_id: str
    invoice_number: str
    invoice_date: date
    period_start: date | None = None
    period_end: date | None = None
    covers_months: list[str] = []
    assigned_month: str | None = None
    hours: float | None = None
    hourly_rate: float | None = None
    rate_currency: str | None = None
    amount: float
    currency: str = "EUR"
    notes: str | None = None


class ProviderInvoiceCreate(ProviderInvoiceBase):
    pass


class ProviderInvoiceUpdate(BaseModel):
    invoice_number: str | None = None
    invoice_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    covers_months: list[str] | None = None
    assigned_month: str | None = None
    hours: float | None = None
    hourly_rate: float | None = None
    rate_currency: str | None = None
    amount: float | None = None
    currency: str | None = None
    notes: str | None = None


class ProviderInvoiceResponse(ProviderInvoiceBase):
    id: int
    file_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
