from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ImportHistory(Base):
    __tablename__ = "import_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_type: Mapped[str] = mapped_column(String)  # "bank" | "upwork"
    original_filename: Mapped[str] = mapped_column(String)
    stored_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
