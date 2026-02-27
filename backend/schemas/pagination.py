"""Pagination schema for list endpoints."""

from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper with items, total count, and offset info."""

    items: list[T]
    total: int
    skip: int
    limit: int
