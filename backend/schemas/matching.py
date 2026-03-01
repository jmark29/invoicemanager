"""Pydantic schemas for transaction matching endpoints."""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class MatchCandidate(BaseModel):
    """A potential match between a bank transaction and a provider invoice."""
    provider_invoice_id: int
    bank_transaction_id: int
    confidence: float  # 0.0 to 1.0
    match_reason: str  # "invoice_number", "amount_date", "category_only"
    # Transaction details
    tx_booking_date: date
    tx_amount_eur: float
    tx_description: str
    # Invoice details
    inv_number: str
    inv_amount: float
    inv_currency: str
    inv_category_id: str


class MatchAction(BaseModel):
    """Request to confirm or reject a suggested match."""
    action: Literal["confirm", "reject"]
    bank_fee: float | None = None  # Optional manual fee entry


class ManualMatchRequest(BaseModel):
    """Request to manually link a transaction to an invoice."""
    provider_invoice_id: int
    bank_fee: float | None = None


class MatchActionResponse(BaseModel):
    """Response after a match action."""
    success: bool
    message: str
    match_status: str | None = None
    amount_eur: float | None = None
    fx_rate: float | None = None
    bank_fee: float | None = None


class MatchStats(BaseModel):
    """Summary statistics from an auto-match operation."""
    auto_matched: int = 0
    suggested: int = 0
    unmatched: int = 0
