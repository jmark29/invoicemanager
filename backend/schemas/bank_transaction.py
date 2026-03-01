"""Pydantic schemas for BankTransaction."""

from datetime import date

from pydantic import BaseModel


class BankTransactionBase(BaseModel):
    booking_date: date
    value_date: date | None = None
    transaction_type: str | None = None
    description: str
    amount_eur: float
    reference: str | None = None
    account_iban: str | None = None
    category_id: str | None = None
    provider_invoice_id: int | None = None
    fx_rate: float | None = None
    bank_fee: float | None = None
    notes: str | None = None


class BankTransactionCreate(BankTransactionBase):
    pass


class BankTransactionUpdate(BaseModel):
    category_id: str | None = None
    provider_invoice_id: int | None = None
    fx_rate: float | None = None
    bank_fee: float | None = None
    notes: str | None = None


class BankTransactionResponse(BankTransactionBase):
    id: int
    match_status: str = "unmatched"
    match_confidence: float | None = None

    model_config = {"from_attributes": True}


class PotentialDuplicateItem(BaseModel):
    booking_date: date
    amount_eur: float
    description: str


class BankImportResponse(BaseModel):
    imported: int
    skipped_duplicate: int
    auto_matched: int
    invoice_auto_matched: int = 0
    invoice_suggested: int = 0
    potential_duplicates: list[PotentialDuplicateItem] = []
    errors: list[str]
