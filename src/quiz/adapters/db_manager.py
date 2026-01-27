import os
import sqlite3

from src.shared.telemetry import Telemetry, measure_time


class DatabaseManager:
    """
    Responsible for:
    1. Managing the SQLite connection lifecycle.
    2. Initializing the database schema (DDL).
    3. Handling migrations.
    """

    def __init__(self, db_path: str = "data/quiz.db") -> None:
        self.db_path = db_path
        self.telemetry = Telemetry("DatabaseManager")
        self._shared_connection: sqlite3.Connection | None = None

        self._ensure_db_exists()

        # For in-memory DBs, we must keep the connection open
        if self.db_path == ":memory:":
            self._shared_connection = sqlite3.connect(
                ":memory:", check_same_thread=False
            )

        self._init_schema()
        self._migrate_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a usable database connection."""
        if self._shared_connection:
            return self._shared_connection
        return sqlite3.connect(self.db_path)

    def close(self) -> None:
        if self._shared_connection:
            self._shared_connection.close()

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
            if not self._shared_connection:
                conn.close()
        except Exception as e:
            self.telemetry.log_error("Schema Init Failed", e)

    def _migrate_schema(self) -> None:
        conn = self.get_connection()
        try:
            cursor = conn.execute("PRAGMA table_info(user_progress)")
            columns = [row[1] for row in cursor.fetchall()]

            if "consecutive_correct" not in columns:
                self.telemetry.log_info("Migrating DB: Adding consecutive_correct")
                conn.execute(
                    "ALTER TABLE user_progress "
                    "ADD COLUMN consecutive_correct INTEGER DEFAULT 0"
                )

            cursor = conn.execute("PRAGMA table_info(questions)")
            q_columns = [row[1] for row in cursor.fetchall()]

            if "category" not in q_columns:
                self.telemetry.log_info("Migrating DB: Adding category column")
                conn.execute(
                    "ALTER TABLE questions ADD COLUMN category TEXT DEFAULT 'Ogólne'"
                )

            conn.commit()
            if not self._shared_connection:
                conn.close()
        except Exception as e:
            self.telemetry.log_error("Migration Failed", e)
