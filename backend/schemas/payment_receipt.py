"""Pydantic schemas for PaymentReceipt."""

from datetime import date

from pydantic import BaseModel


class PaymentReceiptBase(BaseModel):
    client_id: str
    payment_date: date
    amount_eur: float
    reference: str | None = None
    matched_invoice_id: int | None = None
    notes: str | None = None


class PaymentReceiptCreate(PaymentReceiptBase):
    pass


class PaymentReceiptUpdate(BaseModel):
    payment_date: date | None = None
    amount_eur: float | None = None
    reference: str | None = None
    matched_invoice_id: int | None = None
    notes: str | None = None


class PaymentReceiptResponse(PaymentReceiptBase):
    id: int

    model_config = {"from_attributes": True}
