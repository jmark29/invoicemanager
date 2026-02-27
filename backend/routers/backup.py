"""Backup API endpoints."""

from fastapi import APIRouter

from backend.services.backup import backup_database, cleanup_old_backups, list_backups

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.post("", status_code=201)
def create_backup() -> dict:
    """Create a new database backup."""
    path = backup_database()
    cleanup_old_backups(keep=10)
    return {
        "filename": path.name,
        "size_bytes": path.stat().st_size,
    }


@router.get("")
def get_backups() -> list[dict]:
    """List all existing backups."""
    return list_backups()
