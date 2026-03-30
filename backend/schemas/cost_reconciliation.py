"""Pydantic schemas for cost reconciliation (running balance)."""

from datetime import date

from pydantic import BaseModel


class CategoryBalanceResponse(BaseModel):
    category_id: str
    category_name: str
    total_provider_costs: float
    total_invoiced: float
    delta: float
    status: str  # balanced, under_invoiced, over_invoiced


class ProviderInvoiceStatusResponse(BaseModel):
    id: int
    invoice_number: str
    invoice_date: date | None = None
    amount_eur: float
    assigned_month: str | None = None
    linked_invoice_number: str | None = None
    linked_line_item_id: int | None = None
    amount_invoiced: float | None = None
    status: str  # linked, unlinked, amount_mismatch


class CategoryReconciliationDetailResponse(BaseModel):
    category_id: str
    category_name: str
    balance: CategoryBalanceResponse
    provider_invoices: list[ProviderInvoiceStatusResponse] = []


class CostReconciliationSummaryResponse(BaseModel):
    categories: list[CategoryBalanceResponse]
    total_provider_costs: float
    total_invoiced: float
    total_delta: float
    balanced_count: int
    open_count: int


class MissingMonthResponse(BaseModel):
    year: int
    month: int
    label: str  # e.g., "Jul 2025"


class MissingMonthsResponse(BaseModel):
    months: list[MissingMonthResponse]
    total: int
