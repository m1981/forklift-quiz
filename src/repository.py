import sqlite3
import logging
import os
from datetime import date, datetime
from typing import List, Optional
from src.models import Question, UserProfile

logger = logging.getLogger(__name__)

class SQLiteQuizRepository:
    def __init__(self, db_path: str = "data/quiz.db"):
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        self.db_path = db_path
        self._memory_conn = None

        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)

        self._init_db()

    def _get_connection(self):
        if self._memory_conn:
            return self._memory_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        logger.debug("🔍 DB: Checking schema...")
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    streak_days INTEGER DEFAULT 0,
                    last_login DATE,
                    daily_goal INTEGER DEFAULT 3,
                    daily_progress INTEGER DEFAULT 0,
                    last_daily_reset DATE
                )
            """)

    # --- FORENSIC LOGGING: TIME CHECK ---
    def _check_db_time(self):
        """Debug tool to see what time SQLite thinks it is vs Python."""
        with self._get_connection() as conn:
            db_now = conn.execute("SELECT datetime('now')").fetchone()[0]
            py_now = datetime.now()
            logger.debug(f"⏰ TIME CHECK: DB says '{db_now}' | Python says '{py_now}'")

    # --- Question Retrieval ---

    def get_all_questions(self) -> List[Question]:
        try:
            with self._get_connection() as conn:
                logger.debug("🔍 DB: Fetching ALL questions.")
                cursor = conn.execute("SELECT json_data FROM questions")
                questions = [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
                return questions
        except Exception as e:
            logger.error(f"❌ DB ERROR: Fetching questions failed: {e}", exc_info=True)
            return []

    def get_questions_by_ids(self, question_ids: List[str]) -> List[Question]:
        """
        Fetches specific questions by ID. Used for the 'Correction Phase'.
        """
        if not question_ids:
            return []

        placeholders = ','.join(['?'] * len(question_ids))
        try:
            with self._get_connection() as conn:
                logger.debug(f"🔍 DB: Fetching {len(question_ids)} specific questions: {question_ids}")
                cursor = conn.execute(f"SELECT json_data FROM questions WHERE id IN ({placeholders})", question_ids)
                questions = [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
                return questions
        except Exception as e:
            logger.error(f"❌ DB ERROR: Fetching specific questions failed: {e}", exc_info=True)
            return []

    def seed_questions(self, new_questions: List[Question]):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for new_q in new_questions:
                    cursor.execute(
                        "INSERT OR REPLACE INTO questions (id, json_data) VALUES (?, ?)",
                        (new_q.id, new_q.json())
                    )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to seed questions: {e}")

    # --- User Progress ---

    def was_question_answered_today(self, user_id: str, question_id: str) -> bool:
        self._check_db_time() # Log time on every check
        with self._get_connection() as conn:
            logger.debug(f"🕵️‍♂️ DUPLICATE CHECK: User='{user_id}', QID='{question_id}'")
            cursor = conn.execute("""
                SELECT count(*) FROM user_progress 
                WHERE user_id = ? AND question_id = ? AND date(timestamp) = date('now')
            """, (user_id, question_id))
            count = cursor.fetchone()[0]

            if count > 0:
                logger.warning(f"🔁 REPETITION FOUND: Count={count}. Already answered today.")
            else:
                logger.info(f"🆕 FRESH ATTEMPT: Count={count}. First time today.")

            return count > 0

    def get_all_attempted_ids(self, user_id: str) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT question_id FROM user_progress WHERE user_id = ?", (user_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_incorrect_question_ids(self, user_id: str) -> List[str]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0", (user_id,))
            return [row[0] for row in cursor.fetchall()]

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool):
        logger.debug(f"💾 DB WRITE: Attempt User={user_id}, Q={question_id}, Correct={is_correct}")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_progress (user_id, question_id, is_correct)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_id) 
                DO UPDATE SET is_correct=excluded.is_correct, timestamp=CURRENT_TIMESTAMP
            """, (user_id, question_id, is_correct))
            conn.commit()

    def reset_user_progress(self, user_id: str):
        logger.warning(f"🧨 DB: Wiping history for {user_id}")
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
            conn.execute("UPDATE user_profiles SET streak_days=0, daily_progress=0 WHERE user_id = ?", (user_id,))

    # --- User Profile ---

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            today = date.today()

            if not row:
                profile = UserProfile(user_id=user_id)
                conn.execute("""
                    INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress, last_daily_reset)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (profile.user_id, profile.streak_days, today, profile.daily_goal, 0, today))
                return profile

            return UserProfile(
                user_id=row[0],
                streak_days=row[1],
                last_login=datetime.strptime(row[2], "%Y-%m-%d").date() if row[2] else today,
                daily_goal=row[3],
                daily_progress=row[4],
                last_daily_reset=datetime.strptime(row[5], "%Y-%m-%d").date() if row[5] else today
            )

    def save_profile(self, profile: UserProfile):
        logger.debug(f"💾 DB WRITE: Profile {profile.user_id} -> Progress={profile.daily_progress}")
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE user_profiles 
                SET streak_days = ?, last_login = ?, daily_goal = ?, daily_progress = ?, last_daily_reset = ?
                WHERE user_id = ?
            """, (
                profile.streak_days,
                profile.last_login,
                profile.daily_goal,
                profile.daily_progress,
                profile.last_daily_reset,
                profile.user_id
            ))
            conn.commit()

    # --- Debug ---
    def debug_get_user_stats(self, user_id: str) -> dict:
        with self._get_connection() as conn:
            total = conn.execute("SELECT count(*) FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()[0]
            correct = conn.execute("SELECT count(*) FROM user_progress WHERE user_id = ? AND is_correct = 1", (user_id,)).fetchone()[0]
            incorrect = conn.execute("SELECT count(*) FROM user_progress WHERE user_id = ? AND is_correct = 0", (user_id,)).fetchone()[0]
            incorrect_ids = [row[0] for row in conn.execute("SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0", (user_id,)).fetchall()]
            return {"total_attempts": total, "correct_count": correct, "incorrect_count": incorrect, "incorrect_ids": incorrect_ids}