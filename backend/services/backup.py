"""SQLite online backup service.

Uses sqlite3.connection.backup() for safe, consistent backups even while
the database is being written to.
"""

import logging
import sqlite3
from datetime import datetime, UTC
from pathlib import Path

from backend.config import settings

logger = logging.getLogger(__name__)


def _backup_dir() -> Path:
    return settings.DATA_DIR / "backups"


def _db_path() -> Path:
    return settings.DATA_DIR / "invoices.db"


def backup_database() -> Path:
    """Create a timestamped backup of the SQLite database.

    Returns the path to the backup file.
    """
    backup_dir = _backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%f")
    backup_path = backup_dir / f"invoices_{ts}.db"

    source = sqlite3.connect(str(_db_path()))
    dest = sqlite3.connect(str(backup_path))
    source.backup(dest)
    dest.close()
    source.close()

    size_kb = backup_path.stat().st_size / 1024
    logger.info("Database backup created: %s (%.1f KB)", backup_path.name, size_kb)
    return backup_path


def list_backups() -> list[dict]:
    """List existing backup files with timestamps and sizes."""
    backup_dir = _backup_dir()
    if not backup_dir.exists():
        return []

    backups = []
    for f in sorted(backup_dir.glob("invoices_*.db"), reverse=True):
        backups.append({
            "filename": f.name,
            "size_bytes": f.stat().st_size,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime, tz=UTC).isoformat(),
        })
    return backups


def cleanup_old_backups(keep: int = 10) -> int:
    """Remove old backups, keeping the most recent `keep` files.

    Returns the number of files removed.
    """
    backup_dir = _backup_dir()
    if not backup_dir.exists():
        return 0

    files = sorted(backup_dir.glob("invoices_*.db"), reverse=True)
    removed = 0
    for f in files[keep:]:
        f.unlink()
        removed += 1

    if removed:
        logger.info("Cleaned up %d old backups (kept %d)", removed, keep)
    return removed
