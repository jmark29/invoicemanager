"""Pydantic schemas for UpworkTransaction."""

from datetime import date

from pydantic import BaseModel


class UpworkTransactionBase(BaseModel):
    tx_id: str
    tx_date: date
    tx_type: str | None = None
    description: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    amount_eur: float
    freelancer_name: str | None = None
    contract_ref: str | None = None
    category_id: str | None = None
    assigned_month: str | None = None
    assigned_invoice_id: int | None = None


class UpworkTransactionCreate(UpworkTransactionBase):
    pass


class UpworkTransactionUpdate(BaseModel):
    category_id: str | None = None
    assigned_month: str | None = None
    assigned_invoice_id: int | None = None
    freelancer_name: str | None = None
    notes: str | None = None


class UpworkTransactionResponse(UpworkTransactionBase):
    id: int

    model_config = {"from_attributes": True}


class UpworkImportResponse(BaseModel):
    imported: int
    skipped_duplicate: int
    skipped_no_amount: int
    skipped_no_period: int
    errors: list[str]
