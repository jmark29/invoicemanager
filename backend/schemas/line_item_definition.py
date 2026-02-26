"""Pydantic schemas for LineItemDefinition."""

from pydantic import BaseModel


class LineItemDefinitionBase(BaseModel):
    client_id: str
    position: int
    label: str
    source_type: str  # fixed, category, manual
    category_id: str | None = None
    fixed_amount: float | None = None
    is_optional: bool = False
    sort_order: int = 0


class LineItemDefinitionCreate(LineItemDefinitionBase):
    pass


class LineItemDefinitionUpdate(BaseModel):
    position: int | None = None
    label: str | None = None
    source_type: str | None = None
    category_id: str | None = None
    fixed_amount: float | None = None
    is_optional: bool | None = None
    sort_order: int | None = None


class LineItemDefinitionResponse(LineItemDefinitionBase):
    id: int

    model_config = {"from_attributes": True}
