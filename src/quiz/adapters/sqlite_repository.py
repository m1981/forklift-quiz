import sqlite3
import logging
import os
from datetime import date, datetime
from typing import List, Optional

from src.quiz.domain.models import Question, UserProfile
from src.quiz.domain.ports import IQuizRepository

logger = logging.getLogger(__name__)


class SQLiteQuizRepository(IQuizRepository):
    def __init__(self, db_path: str = "data/quiz.db"):
        self.db_path = db_path
        self._shared_connection = None
        self._ensure_db_exists()
        if self.db_path == ":memory:":
            self._shared_connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_schema()

    def _ensure_db_exists(self):
        if self.db_path == ":memory:":
            return
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _get_connection(self):
        if self._shared_connection:
            return self._shared_connection
        return sqlite3.connect(self.db_path)

    def close(self):
        """Explicitly close connection if needed (good for tests)"""
        if self._shared_connection:
            self._shared_connection.close()

    def _init_schema(self):
        # Note: We don't use 'with' here for the connection itself if it's shared,
        # because we don't want to close it. But sqlite3 context manager
        # only handles commit/rollback, not closing, so it is safe.
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    json_data TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id TEXT,
                    question_id TEXT,
                    is_correct BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, question_id)
                )
            """)
            # Updated Schema with has_completed_onboarding
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    streak_days INTEGER DEFAULT 0,
                    last_login DATE,
                    daily_goal INTEGER DEFAULT 3,
                    daily_progress INTEGER DEFAULT 0,
                    last_daily_reset DATE,
                    has_completed_onboarding BOOLEAN DEFAULT 0
                )
            """)
            conn.commit()
        except Exception as e:
            logger.error(f"Schema Init Error: {e}")

    # --- Implementation of Interface ---

    def get_all_questions(self) -> List[Question]:
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT json_data FROM questions")
            return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return []

    def get_questions_by_ids(self, question_ids: List[str]) -> List[Question]:
        if not question_ids: return []
        placeholders = ','.join(['?'] * len(question_ids))
        try:
            conn = self._get_connection()
            cursor = conn.execute(f"SELECT json_data FROM questions WHERE id IN ({placeholders})", question_ids)
            return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"DB Error: {e}")
            return []

    def seed_questions(self, questions: List[Question]):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            for q in questions:
                cursor.execute(
                    "INSERT OR REPLACE INTO questions (id, json_data) VALUES (?, ?)",
                    (q.id, q.json())
                )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to seed questions: {e}")

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        today = date.today()

        if not row:
            profile = UserProfile(user_id=user_id)
            conn.execute("""
                INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress, last_daily_reset, has_completed_onboarding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (profile.user_id, profile.streak_days, today, profile.daily_goal, 0, today, False))
            conn.commit()
            return profile

        # Handle potential schema mismatch if column was added later
        has_onboarding = False
        if len(row) > 6:
            has_onboarding = bool(row[6])

        return UserProfile(
            user_id=row[0],
            streak_days=row[1],
            last_login=datetime.strptime(row[2], "%Y-%m-%d").date() if row[2] else today,
            daily_goal=row[3],
            daily_progress=row[4],
            last_daily_reset=datetime.strptime(row[5], "%Y-%m-%d").date() if row[5] else today,
            has_completed_onboarding=has_onboarding
        )

    def save_profile(self, profile: UserProfile):
        conn = self._get_connection()
        conn.execute("""
            UPDATE user_profiles 
            SET streak_days = ?, last_login = ?, daily_goal = ?, daily_progress = ?, last_daily_reset = ?, has_completed_onboarding = ?
            WHERE user_id = ?
        """, (
            profile.streak_days,
            profile.last_login,
            profile.daily_goal,
            profile.daily_progress,
            profile.last_daily_reset,
            profile.has_completed_onboarding,
            profile.user_id
        ))
        conn.commit()

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool):
        conn = self._get_connection()
        conn.execute("""
            INSERT INTO user_progress (user_id, question_id, is_correct)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, question_id) 
            DO UPDATE SET is_correct=excluded.is_correct, timestamp=CURRENT_TIMESTAMP
        """, (user_id, question_id, is_correct))
        conn.commit()

    def was_question_answered_on_date(self, user_id: str, question_id: str, check_date: date) -> bool:
        date_str = check_date.strftime("%Y-%m-%d")
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT count(*) FROM user_progress 
            WHERE user_id = ? AND question_id = ? AND date(timestamp) = ?
        """, (user_id, question_id, date_str))
        return cursor.fetchone()[0] > 0

    def get_incorrect_question_ids(self, user_id: str) -> List[str]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0", (user_id,))
        return [row[0] for row in cursor.fetchall()]

    def get_all_attempted_ids(self, user_id: str) -> List[str]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT question_id FROM user_progress WHERE user_id = ?", (user_id,))
        return [row[0] for row in cursor.fetchall()]

    def reset_user_progress(self, user_id: str):
        conn = self._get_connection()
        conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE user_profiles SET streak_days=0, daily_progress=0, has_completed_onboarding=0 WHERE user_id = ?", (user_id,))
        conn.commit()