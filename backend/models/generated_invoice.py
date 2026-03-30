from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.client import Client
    from backend.models.invoice_line_item_source import InvoiceLineItemSource
    from backend.models.payment_receipt import PaymentReceipt
    from backend.models.upwork_transaction import UpworkTransaction


class GeneratedInvoice(Base):
    __tablename__ = "generated_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    invoice_number: Mapped[str] = mapped_column(String, unique=True)
    invoice_number_display: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    filename: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    period_year: Mapped[int] = mapped_column(Integer)
    period_month: Mapped[int] = mapped_column(Integer)
    invoice_date: Mapped[date] = mapped_column(Date)
    net_total: Mapped[float] = mapped_column(Float)
    vat_amount: Mapped[float] = mapped_column(Float)
    gross_total: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft, sent, paid, overdue
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pdf_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sent_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Sprint 4: import support
    source: Mapped[str] = mapped_column(String, default="generated")  # generated, imported
    original_file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    period_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    period_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    client: Mapped["Client"] = relationship(back_populates="generated_invoices")
    items: Mapped[list["GeneratedInvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    payment_receipts: Mapped[list["PaymentReceipt"]] = relationship(
        back_populates="matched_invoice"
    )
    upwork_transactions: Mapped[list["UpworkTransaction"]] = relationship(
        back_populates="assigned_invoice"
    )


class GeneratedInvoiceItem(Base):
    __tablename__ = "generated_invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("generated_invoices.id"))
    position: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    source_type: Mapped[str] = mapped_column(String)  # fixed, direct, distributed, upwork, manual
    category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cost_categories.id"), nullable=True
    )
    provider_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("provider_invoices.id"), nullable=True
    )
    distribution_source_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("provider_invoices.id"), nullable=True
    )
    distribution_months_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    upwork_tx_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Sprint 4: link to line item definition config
    line_item_config_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("line_item_definitions.id"), nullable=True
    )

    invoice: Mapped["GeneratedInvoice"] = relationship(back_populates="items")
    sources: Mapped[list["InvoiceLineItemSource"]] = relationship(
        back_populates="line_item", cascade="all, delete-orphan"
    )
