import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.bank_transaction import BankTransaction
    from backend.models.cost_category import CostCategory


class ProviderInvoice(Base):
    __tablename__ = "provider_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[str] = mapped_column(ForeignKey("cost_categories.id"))
    invoice_number: Mapped[str] = mapped_column(String)
    invoice_date: Mapped[date] = mapped_column(Date)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    _covers_months: Mapped[Optional[str]] = mapped_column("covers_months", Text, nullable=True)
    assigned_month: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. "2025-01"
    hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hourly_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rate_currency: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String, default="EUR")
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Sprint 2: matching and FX tracking
    payment_status: Mapped[str] = mapped_column(String, default="unpaid")  # unpaid, matched, paid, partial
    matched_transaction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("bank_transactions.id", use_alter=True), nullable=True
    )
    amount_eur: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # EUR bank debit
    bank_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # banking/FX fee
    fx_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # effective exchange rate

    category: Mapped["CostCategory"] = relationship(back_populates="provider_invoices")
    bank_transactions: Mapped[list["BankTransaction"]] = relationship(
        back_populates="provider_invoice",
        foreign_keys="BankTransaction.provider_invoice_id",
    )
    matched_transaction: Mapped[Optional["BankTransaction"]] = relationship(
        foreign_keys=[matched_transaction_id],
    )

    @property
    def covers_months(self) -> list[str]:
        if self._covers_months:
            return json.loads(self._covers_months)
        return []

    @covers_months.setter
    def covers_months(self, value: list[str]) -> None:
        self._covers_months = json.dumps(value)
