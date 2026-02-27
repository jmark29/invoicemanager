"""Database session management for MCP server tools."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from backend.database import SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Create a scoped DB session for a single tool/resource call."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
