from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.client import Client
    from backend.models.generated_invoice import GeneratedInvoice


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    payment_date: Mapped[date] = mapped_column(Date)
    amount_eur: Mapped[float] = mapped_column(Float)
    reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    matched_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("generated_invoices.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="payment_receipts")
    matched_invoice: Mapped[Optional["GeneratedInvoice"]] = relationship(
        back_populates="payment_receipts"
    )
