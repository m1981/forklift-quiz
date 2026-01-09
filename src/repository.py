import sqlite3
import json
from typing import List, Optional
from src.models import Question

class SQLiteQuizRepository:
    def __init__(self, db_path: str = "data/quiz.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Table for static questions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    json_data TEXT
                )
            """)
            # Table for user progress
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id TEXT,
                    question_id TEXT,
                    is_correct BOOLEAN,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, question_id)
                )
            """)

    def seed_questions(self, questions: List[Question]):
        """Populates DB from JSON if empty or updates existing."""
        with sqlite3.connect(self.db_path) as conn:
            for q in questions:
                conn.execute(
                    "INSERT OR REPLACE INTO questions (id, json_data) VALUES (?, ?)",
                    (q.id, q.json())
                )

    def get_all_questions(self) -> List[Question]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT json_data FROM questions")
            return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]

    def get_question_by_id(self, q_id: str) -> Optional[Question]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT json_data FROM questions WHERE id = ?", (q_id,))
            row = cursor.fetchone()
            return Question.model_validate_json(row[0]) if row else None

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_progress (user_id, question_id, is_correct)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_id) 
                DO UPDATE SET is_correct=excluded.is_correct, timestamp=CURRENT_TIMESTAMP
            """, (user_id, question_id, is_correct))

    def get_incorrect_question_ids(self, user_id: str) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0",
                (user_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    def reset_user_progress(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))