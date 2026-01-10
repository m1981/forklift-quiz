import sqlite3
import logging
import os
from typing import List, Optional
from src.models import Question

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SQLiteQuizRepository:
    def __init__(self, db_path: str = "data/quiz.db"):
        # 1. Handle Directory Creation (Prevent FileNotFoundError)
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        self.db_path = db_path
        self._memory_conn = None

        # 2. Handle In-Memory Persistence (The Fix for TDD)
        if self.db_path == ":memory:":
            # We must keep this reference alive, otherwise the DB is garbage collected immediately
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)

        self._init_db()

    def _get_connection(self):
        """
        Returns a database connection.
        If using :memory:, returns the persistent shared connection.
        If using a file, creates a new connection (standard SQLite pattern).
        """
        if self._memory_conn:
            return self._memory_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initialize the database schema."""
        # Note: 'with conn:' handles transaction commit/rollback, it does NOT close the connection.
        with self._get_connection() as conn:
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

    def get_all_questions(self) -> List[Question]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT json_data FROM questions")
                return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching questions: {e}")
            return []

    def get_question_by_id(self, q_id: str) -> Optional[Question]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT json_data FROM questions WHERE id = ?", (q_id,))
                row = cursor.fetchone()
                return Question.model_validate_json(row[0]) if row else None
        except Exception:
            return None

    def seed_questions(self, new_questions: List[Question]):
        """
        Smart Seeding:
        1. Updates question text/images.
        2. If the CORRECT ANSWER changes, resets user progress for that question.
        """
        try:
            # Load existing questions to compare
            existing_questions = {q.id: q for q in self.get_all_questions()}

            with self._get_connection() as conn:
                cursor = conn.cursor()

                for new_q in new_questions:
                    old_q = existing_questions.get(new_q.id)

                    # Check if critical logic changed (The Answer Key)
                    if old_q and old_q.correct_option != new_q.correct_option:
                        logger.warning(f"⚠️ Answer key changed for Q{new_q.id}. Resetting user progress.")
                        cursor.execute("DELETE FROM user_progress WHERE question_id = ?", (new_q.id,))

                    cursor.execute(
                        "INSERT OR REPLACE INTO questions (id, json_data) VALUES (?, ?)",
                        (new_q.id, new_q.json())
                    )

                conn.commit()

        except sqlite3.Error as e:
            logger.error(f"Failed to seed questions: {e}")

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_progress (user_id, question_id, is_correct)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_id) 
                DO UPDATE SET is_correct=excluded.is_correct, timestamp=CURRENT_TIMESTAMP
            """, (user_id, question_id, is_correct))
            conn.commit()

    def get_incorrect_question_ids(self, user_id: str) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def reset_user_progress(self, user_id: str):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
            conn.commit()