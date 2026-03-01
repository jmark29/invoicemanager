from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.cost_category import CostCategory
    from backend.models.provider_invoice import ProviderInvoice


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    booking_date: Mapped[date] = mapped_column(Date)
    value_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    transaction_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    amount_eur: Mapped[float] = mapped_column(Float)  # negative = outgoing
    reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    account_iban: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cost_categories.id"), nullable=True
    )
    provider_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("provider_invoices.id"), nullable=True
    )
    fx_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bank_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sprint 2: matching
    match_status: Mapped[str] = mapped_column(String, default="unmatched")  # auto_matched, suggested, manual, unmatched, rejected
    match_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0

    category: Mapped[Optional["CostCategory"]] = relationship(
        back_populates="bank_transactions"
    )
    provider_invoice: Mapped[Optional["ProviderInvoice"]] = relationship(
        back_populates="bank_transactions",
        foreign_keys=[provider_invoice_id],
    )
