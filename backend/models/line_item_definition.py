from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.client import Client
    from backend.models.cost_category import CostCategory


class LineItemDefinition(Base):
    __tablename__ = "line_item_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"))
    position: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String)  # fixed, category, manual
    category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("cost_categories.id"), nullable=True
    )
    fixed_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    client: Mapped["Client"] = relationship(back_populates="line_item_definitions")
    category: Mapped[Optional["CostCategory"]] = relationship(
        back_populates="line_item_definitions"
    )
