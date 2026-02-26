from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.generated_invoice import GeneratedInvoice
    from backend.models.line_item_definition import LineItemDefinition
    from backend.models.payment_receipt import PaymentReceipt


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    client_number: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    address_line1: Mapped[str] = mapped_column(String)
    address_line2: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    zip_city: Mapped[str] = mapped_column(String)
    vat_rate: Mapped[float] = mapped_column(Float, default=0.19)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    line_item_definitions: Mapped[list["LineItemDefinition"]] = relationship(
        back_populates="client"
    )
    generated_invoices: Mapped[list["GeneratedInvoice"]] = relationship(
        back_populates="client"
    )
    payment_receipts: Mapped[list["PaymentReceipt"]] = relationship(
        back_populates="client"
    )
