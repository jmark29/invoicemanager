from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class WorkingDaysConfig(Base):
    __tablename__ = "working_days_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String, default="DE")
    state: Mapped[str] = mapped_column(String, default="HE")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
