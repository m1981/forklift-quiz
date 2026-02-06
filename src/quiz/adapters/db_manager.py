import os
import sqlite3
from typing import Any

from src.shared.telemetry import Telemetry, measure_time


class DatabaseManager:
    """
    Responsible for:
    1. Managing the SQLite connection lifecycle.
    2. Initializing the database schema (DDL).
    3. Handling migrations.
    4. Ensuring pickle-safety for Streamlit Session State.
    """

    def __init__(self, db_path: str = "data/quiz.db") -> None:
        self.db_path = db_path
        self.telemetry = Telemetry("DatabaseManager")
        self._shared_connection: sqlite3.Connection | None = None

        self._ensure_db_exists()

        # For in-memory DBs, we must keep the connection open immediately
        if self.db_path == ":memory:":
            self._shared_connection = sqlite3.connect(
                ":memory:", check_same_thread=False
            )

        self._init_schema()
        self._migrate_schema()

    # --- SERIALIZATION LOGIC (Pickle Safety) ---
    def __getstate__(self) -> dict[str, Any]:
        """
        Called when Streamlit/Pickle saves the session.
        We must remove the SQLite connection object because it cannot be pickled.
        """
        state = self.__dict__.copy()
        # Remove the unpickleable connection object
        if "_shared_connection" in state:
            del state["_shared_connection"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """
        Called when Streamlit/Pickle restores the session.
        We restore the state and reset the connection to None.
        It will be lazily re-created by get_connection().
        """
        self.__dict__.update(state)
        self._shared_connection = None
        # Note: If using ":memory:", data is lost here.
        # This architecture assumes file-based SQLite for persistence.

    def get_connection(self) -> sqlite3.Connection:
        """Returns a usable database connection, reconnecting if necessary."""
        # If we have a live connection, use it
        if self._shared_connection:
            try:
                # Optional: Check if connection is actually alive
                self._shared_connection.execute("SELECT 1")
                return self._shared_connection
            except sqlite3.ProgrammingError:
                # Connection was closed externally
                self._shared_connection = None

        # Create new connection
        conn = sqlite3.connect(self.db_path, check_same_thread=False)

        # Optimization: Enable WAL mode for better concurrency
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode=WAL")

        self._shared_connection = conn
        return conn

    def close(self) -> None:
        if self._shared_connection:
            self._shared_connection.close()
            self._shared_connection = None

    def _ensure_db_exists(self) -> None:
        if self.db_path == ":memory:":
            return
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    @measure_time("db_init_schema")
    def _init_schema(self) -> None:
        conn = self.get_connection()
        try:
            # Questions Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS questions
                (
                    id
                    TEXT
                    PRIMARY
                    KEY,
                    category
                    TEXT,
                    json_data
                    TEXT
                )
                """
            )

            # User Progress Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_progress
                (
                    user_id
                    TEXT,
                    question_id
                    TEXT,
                    is_correct
                    BOOLEAN,
                    consecutive_correct
                    INTEGER
                    DEFAULT
                    0,
                    timestamp
                    DATETIME
                    DEFAULT
                    CURRENT_TIMESTAMP,
                    PRIMARY
                    KEY
                (
                    user_id,
                    question_id
                )
                    )
                """
            )

            # User Profiles
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles
                (
                    user_id
                    TEXT
                    PRIMARY
                    KEY,
                    streak_days
                    INTEGER
                    DEFAULT
                    0,
                    last_login
                    DATE,
                    daily_goal
                    INTEGER
                    DEFAULT
                    3,
                    daily_progress
                    INTEGER
                    DEFAULT
                    0,
                    last_daily_reset
                    DATE,
                    has_completed_onboarding
                    BOOLEAN
                    DEFAULT
                    0
                )
                """
            )
            conn.commit()
        except Exception as e:
            self.telemetry.log_error("Schema Init Failed", e)
            # Do not close shared connection here if we want to keep it open

    def _migrate_schema(self) -> None:
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Check user_profiles columns
            cursor.execute("PRAGMA table_info(user_profiles)")
            columns = [info[1] for info in cursor.fetchall()]

            # Migration: Add preferred_language if missing
            if "preferred_language" not in columns:
                self.telemetry.log_info(
                    "Migrating: Adding preferred_language to user_profiles"
                )
                cursor.execute(
                    "ALTER TABLE user_profiles ADD COLUMN preferred_language TEXT DEFAULT 'pl'"
                )

            # Migration: Add metadata if missing (for Demo Mode)
            if "metadata" not in columns:
                self.telemetry.log_info("Migrating: Adding metadata to user_profiles")
                # SQLite doesn't have native JSON type like Postgres, TEXT is fine
                cursor.execute(
                    "ALTER TABLE user_profiles ADD COLUMN metadata TEXT DEFAULT '{}'"
                )

            conn.commit()
        except Exception as e:
            self.telemetry.log_error("Schema migration failed", e)
        finally:
            if not self._shared_connection:
                conn.close()
