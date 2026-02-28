"""Pydantic schemas for CompanySettings."""

from pydantic import BaseModel


class CompanySettingsResponse(BaseModel):
    id: int
    company_name: str
    address_line1: str
    address_line2: str | None = None
    zip_city: str
    managing_director: str | None = None
    tax_number: str | None = None
    vat_id: str | None = None
    bank_name: str | None = None
    iban: str | None = None
    bic: str | None = None
    email: str | None = None
    phone: str | None = None
    fax: str | None = None
    website: str | None = None
    register_info: str | None = None

    model_config = {"from_attributes": True}


class CompanySettingsUpdate(BaseModel):
    company_name: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    zip_city: str | None = None
    managing_director: str | None = None
    tax_number: str | None = None
    vat_id: str | None = None
    bank_name: str | None = None
    iban: str | None = None
    bic: str | None = None
    email: str | None = None
    phone: str | None = None
    fax: str | None = None
    website: str | None = None
    register_info: str | None = None
