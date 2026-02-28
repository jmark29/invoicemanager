"""Pydantic schemas for ImportHistory."""

from datetime import datetime

from pydantic import BaseModel


class ImportHistoryResponse(BaseModel):
    id: int
    file_type: str
    original_filename: str
    stored_path: str | None = None
    imported_at: datetime
    record_count: int
    skipped_count: int
    notes: str | None = None

    model_config = {"from_attributes": True}
