import os
import pickle
import sqlite3

import pytest

from src.quiz.adapters.db_manager import DatabaseManager


class TestDatabaseManagerInit:
    def test_init_creates_file_db(self, tmp_path):
        """Test initialization creates database file."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        assert os.path.exists(db_path)
        db.close()

    def test_init_creates_directory_if_missing(self, tmp_path):
        """Test initialization creates parent directories."""
        db_path = str(tmp_path / "subdir" / "nested" / "test.db")
        db = DatabaseManager(db_path)

        assert os.path.exists(db_path)
        db.close()

    def test_init_memory_db_keeps_connection_open(self):
        """Test in-memory DB keeps connection open immediately."""
        db = DatabaseManager(":memory:")

        assert db._shared_connection is not None
        assert db._shared_connection.execute("SELECT 1").fetchone() == (1,)
        db.close()

    def test_init_creates_all_tables(self, tmp_path):
        """Test initialization creates all required tables."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)
        conn = db.get_connection()

        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "questions" in tables
        assert "user_progress" in tables
        assert "user_profiles" in tables

        db.close()


class TestConnectionManagement:
    def test_get_connection_returns_working_connection(self, tmp_path):
        """Test get_connection returns a usable connection."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        conn = db.get_connection()
        result = conn.execute("SELECT 1").fetchone()

        assert result == (1,)
        db.close()

    def test_get_connection_reuses_existing_connection(self, tmp_path):
        """Test get_connection reuses the same connection."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        conn1 = db.get_connection()
        conn2 = db.get_connection()

        assert conn1 is conn2
        db.close()

    def test_get_connection_reconnects_after_close(self, tmp_path):
        """Test get_connection creates new connection after close."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        conn1 = db.get_connection()
        db.close()
        conn2 = db.get_connection()

        assert conn1 is not conn2
        assert conn2.execute("SELECT 1").fetchone() == (1,)
        db.close()

    def test_get_connection_handles_closed_connection(self, tmp_path):
        """Test get_connection recovers from externally closed connection."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        conn1 = db.get_connection()
        conn1.close()  # Simulate external close

        conn2 = db.get_connection()
        assert conn2.execute("SELECT 1").fetchone() == (1,)
        db.close()

    def test_get_connection_enables_wal_mode(self, tmp_path):
        """Test get_connection enables WAL mode for file DBs."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        conn = db.get_connection()
        result = conn.execute("PRAGMA journal_mode").fetchone()

        assert result[0].lower() == "wal"
        db.close()

    def test_get_connection_skips_wal_for_memory(self):
        """Test get_connection doesn't enable WAL for in-memory DBs."""
        db = DatabaseManager(":memory:")

        conn = db.get_connection()
        result = conn.execute("PRAGMA journal_mode").fetchone()

        # Memory DBs use 'memory' journal mode
        assert result[0].lower() == "memory"
        db.close()

    def test_close_closes_connection(self, tmp_path):
        """Test close() properly closes the connection."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        conn = db.get_connection()
        db.close()

        assert db._shared_connection is None

        # Verify connection is actually closed
        with pytest.raises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_close_handles_no_connection(self, tmp_path):
        """Test close() handles case when no connection exists."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        # Should not raise
        db.close()
        db.close()  # Double close


class TestPickleSafety:
    def test_getstate_removes_connection(self, tmp_path):
        """Test __getstate__ removes unpickleable connection."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)
        db.get_connection()  # Create connection

        state = db.__getstate__()

        assert "_shared_connection" not in state
        assert "db_path" in state
        assert "telemetry" in state
        db.close()

    def test_setstate_resets_connection(self, tmp_path):
        """Test __setstate__ resets connection to None."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)
        db.get_connection()

        state = db.__getstate__()
        db.__setstate__(state)

        assert db._shared_connection is None
        db.close()

    def test_pickle_roundtrip_works(self, tmp_path):
        """Test DatabaseManager can be pickled and unpickled."""
        db_path = str(tmp_path / "test.db")
        db1 = DatabaseManager(db_path)
        db1.get_connection()

        # Pickle and unpickle
        pickled = pickle.dumps(db1)
        db2 = pickle.loads(pickled)

        # Verify it works after unpickling
        conn = db2.get_connection()
        assert conn.execute("SELECT 1").fetchone() == (1,)

        db1.close()
        db2.close()

    def test_pickle_preserves_db_path(self, tmp_path):
        """Test pickling preserves database path."""
        db_path = str(tmp_path / "test.db")
        db1 = DatabaseManager(db_path)

        pickled = pickle.dumps(db1)
        db2 = pickle.loads(pickled)

        assert db2.db_path == db_path
        db1.close()
        db2.close()


class TestSchemaMigration:
    def test_migration_adds_demo_prospect_slug(self, tmp_path):
        """Test migration adds demo_prospect_slug column if missing."""
        db_path = str(tmp_path / "test.db")

        # Create DB without the column
        conn = sqlite3.connect(db_path)
        conn.execute("""
                     CREATE TABLE user_profiles
                     (
                         user_id     TEXT PRIMARY KEY,
                         streak_days INTEGER DEFAULT 0
                     )
                     """)
        conn.commit()
        conn.close()

        # Initialize DatabaseManager (should run migration)
        db = DatabaseManager(db_path)

        # Verify column was added
        cursor = db.get_connection().cursor()
        cursor.execute("PRAGMA table_info(user_profiles)")
        columns = {row[1] for row in cursor.fetchall()}

        assert "demo_prospect_slug" in columns
        db.close()

    def test_migration_skips_if_column_exists(self, tmp_path):
        """Test migration doesn't fail if column already exists."""
        db_path = str(tmp_path / "test.db")

        # Create DB with the column
        conn = sqlite3.connect(db_path)
        conn.execute("""
                     CREATE TABLE user_profiles
                     (
                         user_id            TEXT PRIMARY KEY,
                         demo_prospect_slug TEXT DEFAULT NULL
                     )
                     """)
        conn.commit()
        conn.close()

        # Should not raise
        db = DatabaseManager(db_path)
        db.close()


class TestErrorHandling:
    def test_init_schema_handles_errors_gracefully(self, tmp_path):
        """Test _init_schema logs errors but doesn't crash."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        # Corrupt the database
        conn = db.get_connection()
        conn.execute("DROP TABLE questions")
        conn.commit()

        # Should not raise, just log
        db._init_schema()
        db.close()

    def test_migrate_schema_handles_errors_gracefully(self, tmp_path):
        """Test _migrate_schema logs errors but doesn't crash."""
        db_path = str(tmp_path / "test.db")
        db = DatabaseManager(db_path)

        # Drop the table to cause migration to fail
        conn = db.get_connection()
        conn.execute("DROP TABLE user_profiles")
        conn.commit()

        # Should not raise, just log
        db._migrate_schema()
        db.close()
