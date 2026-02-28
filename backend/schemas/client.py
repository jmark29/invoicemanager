"""Pydantic schemas for Client."""

from pydantic import BaseModel


class ClientBase(BaseModel):
    client_number: str
    name: str
    address_line1: str
    address_line2: str | None = None
    zip_city: str
    country: str | None = "Deutschland"
    vat_id: str | None = None
    contact_person: str | None = None
    email: str | None = None
    payment_terms_days: int | None = 14
    notes: str | None = None
    vat_rate: float = 0.19
    active: bool = True


class ClientCreate(ClientBase):
    id: str


class ClientUpdate(BaseModel):
    client_number: str | None = None
    name: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    zip_city: str | None = None
    country: str | None = None
    vat_id: str | None = None
    contact_person: str | None = None
    email: str | None = None
    payment_terms_days: int | None = None
    notes: str | None = None
    vat_rate: float | None = None
    active: bool | None = None


class ClientResponse(ClientBase):
    id: str

    model_config = {"from_attributes": True}
