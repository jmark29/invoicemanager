import json
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.bank_transaction import BankTransaction
    from backend.models.line_item_definition import LineItemDefinition
    from backend.models.provider_invoice import ProviderInvoice
    from backend.models.upwork_transaction import UpworkTransaction


class CostCategory(Base):
    __tablename__ = "cost_categories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    provider_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    provider_location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rate_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    billing_cycle: Mapped[str] = mapped_column(String)  # monthly, quarterly, weekly, irregular
    cost_type: Mapped[str] = mapped_column(String)  # direct, distributed, upwork, fixed
    distribution_method: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # working_days, equal
    vat_status: Mapped[str] = mapped_column(String, default="standard")  # standard, exempt, reverse_charge
    _bank_keywords: Mapped[Optional[str]] = mapped_column("bank_keywords", Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    provider_invoices: Mapped[list["ProviderInvoice"]] = relationship(
        back_populates="category"
    )
    bank_transactions: Mapped[list["BankTransaction"]] = relationship(
        back_populates="category"
    )
    line_item_definitions: Mapped[list["LineItemDefinition"]] = relationship(
        back_populates="category"
    )
    upwork_transactions: Mapped[list["UpworkTransaction"]] = relationship(
        back_populates="category"
    )

    @property
    def bank_keywords(self) -> list[str]:
        if self._bank_keywords:
            return json.loads(self._bank_keywords)
        return []

    @bank_keywords.setter
    def bank_keywords(self, value: list[str]) -> None:
        self._bank_keywords = json.dumps(value, ensure_ascii=False)
