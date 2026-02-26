"""Pydantic schemas for CostCategory."""

from pydantic import BaseModel


class CostCategoryBase(BaseModel):
    name: str
    provider_name: str | None = None
    provider_location: str | None = None
    currency: str = "EUR"
    hourly_rate: float | None = None
    rate_currency: str | None = None
    billing_cycle: str  # monthly, quarterly, weekly, irregular
    cost_type: str  # direct, distributed, upwork, fixed
    distribution_method: str | None = None
    vat_status: str = "standard"
    bank_keywords: list[str] = []
    notes: str | None = None
    active: bool = True
    sort_order: int = 0


class CostCategoryCreate(CostCategoryBase):
    id: str


class CostCategoryUpdate(BaseModel):
    name: str | None = None
    provider_name: str | None = None
    provider_location: str | None = None
    currency: str | None = None
    hourly_rate: float | None = None
    rate_currency: str | None = None
    billing_cycle: str | None = None
    cost_type: str | None = None
    distribution_method: str | None = None
    vat_status: str | None = None
    bank_keywords: list[str] | None = None
    notes: str | None = None
    active: bool | None = None
    sort_order: int | None = None


class CostCategoryResponse(CostCategoryBase):
    id: str

    model_config = {"from_attributes": True}
