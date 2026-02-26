from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.cost_category import CostCategory
    from backend.models.generated_invoice import GeneratedInvoice


class UpworkTransaction(Base):
    __tablename__ = "upwork_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tx_id: Mapped[str] = mapped_column(String, unique=True)
    tx_date: Mapped[date] = mapped_column(Date)
    tx_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    amount_eur: Mapped[float] = mapped_column(Float)
    freelancer_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contract_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cost_categories.id"), nullable=True
    )
    assigned_month: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # e.g. "2026-02"
    assigned_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("generated_invoices.id"), nullable=True
    )

    category: Mapped[Optional["CostCategory"]] = relationship(
        back_populates="upwork_transactions"
    )
    assigned_invoice: Mapped[Optional["GeneratedInvoice"]] = relationship(
        back_populates="upwork_transactions"
    )
