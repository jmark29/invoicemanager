"""Tests for SQLite backup service and API."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.backup import backup_database, cleanup_old_backups, list_backups


@pytest.fixture
def backup_env(tmp_path):
    """Patch settings to use a temp directory with a real SQLite DB."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    db_path = data_dir / "invoices.db"

    # Create a minimal SQLite DB
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello')")
    conn.commit()
    conn.close()

    with patch("backend.services.backup.settings") as mock_settings:
        mock_settings.DATA_DIR = data_dir
        yield data_dir


class TestBackupDatabase:
    def test_creates_backup_file(self, backup_env):
        path = backup_database()
        assert path.exists()
        assert path.name.startswith("invoices_")
        assert path.suffix == ".db"

    def test_backup_is_valid_sqlite(self, backup_env):
        path = backup_database()
        conn = sqlite3.connect(str(path))
        rows = conn.execute("SELECT * FROM test").fetchall()
        conn.close()
        assert rows == [(1, "hello")]

    def test_backup_dir_created(self, backup_env):
        backup_database()
        assert (backup_env / "backups").is_dir()


class TestListBackups:
    def test_empty_when_no_backups(self, backup_env):
        assert list_backups() == []

    def test_lists_created_backups(self, backup_env):
        backup_database()
        backup_database()
        backups = list_backups()
        assert len(backups) == 2
        assert all("filename" in b for b in backups)
        assert all("size_bytes" in b for b in backups)

    def test_sorted_newest_first(self, backup_env):
        import time

        backup_database()
        time.sleep(0.05)
        backup_database()
        backups = list_backups()
        assert backups[0]["created_at"] >= backups[1]["created_at"]


class TestCleanupOldBackups:
    def test_keeps_recent_removes_old(self, backup_env):
        import time

        for _ in range(5):
            backup_database()
            time.sleep(0.05)

        removed = cleanup_old_backups(keep=2)
        assert removed == 3
        assert len(list_backups()) == 2

    def test_noop_when_fewer_than_keep(self, backup_env):
        backup_database()
        removed = cleanup_old_backups(keep=10)
        assert removed == 0

    def test_noop_when_no_backups(self, backup_env):
        removed = cleanup_old_backups(keep=10)
        assert removed == 0


class TestBackupAPI:
    def test_create_backup(self, client):
        with patch("backend.routers.backup.backup_database") as mock_backup, \
             patch("backend.routers.backup.cleanup_old_backups"):
            mock_path = Path("/tmp/invoices_test.db")
            mock_path.touch()
            mock_backup.return_value = mock_path
            response = client.post("/api/backups")
            assert response.status_code == 201
            data = response.json()
            assert data["filename"] == "invoices_test.db"
            mock_path.unlink()

    def test_list_backups(self, client):
        with patch("backend.routers.backup.list_backups") as mock_list:
            mock_list.return_value = [
                {"filename": "invoices_20260226.db", "size_bytes": 1024, "created_at": "2026-02-26T00:00:00+00:00"}
            ]
            response = client.get("/api/backups")
            assert response.status_code == 200
            assert len(response.json()) == 1
