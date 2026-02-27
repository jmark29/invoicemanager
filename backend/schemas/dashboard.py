"""Pydantic schemas for dashboard and reconciliation endpoints."""

from datetime import date

from pydantic import BaseModel

from backend.schemas.generated_invoice import (
    GeneratedInvoiceItemResponse,
    GeneratedInvoiceListResponse,
)


# ── Monthly dashboard ────────────────────────────────────────────


class MonthlyDashboardResponse(BaseModel):
    year: int
    month: int
    has_invoice: bool
    invoice: GeneratedInvoiceListResponse | None = None
    items: list[GeneratedInvoiceItemResponse] = []
    net_total: float = 0.0
    vat_amount: float = 0.0
    gross_total: float = 0.0
    payment_total: float = 0.0
    payment_balance: float = 0.0


# ── Open invoices ────────────────────────────────────────────────


class OpenInvoicesResponse(BaseModel):
    invoices: list[GeneratedInvoiceListResponse]
    count: int
    total_gross: float
    total_net: float


# ── Reconciliation ───────────────────────────────────────────────


class ProviderInvoiceMatchResponse(BaseModel):
    category_id: str
    category_name: str
    invoice_number: str
    invoice_amount: float
    has_bank_payment: bool
    bank_amount: float | None = None
    bank_booking_date: date | None = None


class UnmatchedBankTransactionResponse(BaseModel):
    id: int
    booking_date: date
    amount_eur: float
    description: str
    category_id: str | None = None


class InvoicePaymentStatusResponse(BaseModel):
    invoice_number: str
    status: str
    gross_total: float
    total_paid: float
    balance: float


class ReconciliationResponse(BaseModel):
    year: int
    month: int
    provider_matches: list[ProviderInvoiceMatchResponse]
    matched_count: int
    unmatched_count: int
    unmatched_bank_transactions: list[UnmatchedBankTransactionResponse]
    invoice_status: InvoicePaymentStatusResponse | None = None
