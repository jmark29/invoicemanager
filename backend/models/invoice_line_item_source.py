"""InvoiceLineItemSource — links line items to contributing provider invoices.

Enables many-to-many traceability: multiple provider invoices can contribute
to a single outgoing invoice line item (e.g., two Aeologic invoices summed
into one position), and each contribution records the amount.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.generated_invoice import GeneratedInvoiceItem
    from backend.models.provider_invoice import ProviderInvoice


class InvoiceLineItemSource(Base):
    __tablename__ = "invoice_line_item_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    line_item_id: Mapped[int] = mapped_column(
        ForeignKey("generated_invoice_items.id", ondelete="CASCADE")
    )
    provider_invoice_id: Mapped[int] = mapped_column(
        ForeignKey("provider_invoices.id")
    )
    amount_contributed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )

    line_item: Mapped["GeneratedInvoiceItem"] = relationship(back_populates="sources")
    provider_invoice: Mapped["ProviderInvoice"] = relationship()
