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


class SuggestedMatchResponse(BaseModel):
    """A suggested match between a bank transaction and provider invoice."""
    bank_transaction_id: int
    provider_invoice_id: int
    confidence: float
    match_reason: str
    # Bank transaction details
    tx_booking_date: date
    tx_amount_eur: float
    tx_description: str
    tx_category_id: str | None = None
    # Provider invoice details
    inv_invoice_number: str
    inv_amount: float
    inv_currency: str
    inv_category_id: str


class CompletedMatchResponse(BaseModel):
    """A completed match with FX/fee details."""
    bank_transaction_id: int
    provider_invoice_id: int
    match_status: str
    # Bank transaction details
    tx_booking_date: date
    tx_amount_eur: float
    tx_description: str
    # Provider invoice details
    inv_invoice_number: str
    inv_amount: float
    inv_currency: str
    inv_category_id: str
    # Computed FX/fee values
    amount_eur: float | None = None
    fx_rate: float | None = None
    bank_fee: float | None = None


class UnmatchedInvoiceResponse(BaseModel):
    """A provider invoice without a matched bank payment."""
    id: int
    invoice_number: str
    invoice_date: date
    amount: float
    currency: str
    category_id: str
    assigned_month: str | None = None


class ReconciliationResponse(BaseModel):
    year: int
    month: int
    provider_matches: list[ProviderInvoiceMatchResponse]
    matched_count: int
    unmatched_count: int
    unmatched_bank_transactions: list[UnmatchedBankTransactionResponse]
    suggested_matches: list[SuggestedMatchResponse] = []
    completed_matches: list[CompletedMatchResponse] = []
    unmatched_invoices: list[UnmatchedInvoiceResponse] = []
    invoice_status: InvoicePaymentStatusResponse | None = None
