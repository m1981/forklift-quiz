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
                logger.debug("🔍 DB: Fetching ALL questions from 'questions' table.")
                cursor = conn.execute("SELECT json_data FROM questions")
                questions = [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
                logger.debug(f"🔍 DB: Successfully deserialized {len(questions)} questions.")
                return questions
        except Exception as e:
            logger.error(f"❌ DB ERROR: Fetching questions failed: {e}", exc_info=True)
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

    # --- User Progress (Attempts) ---

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
            cursor = conn.execute(
                "SELECT question_id FROM user_progress WHERE user_id = ?",
                (user_id,)
            )
            results = [row[0] for row in cursor.fetchall()]
            logger.debug(f"🔍 DB: Found {len(results)} attempted questions for {user_id}.")
            return results

    def get_incorrect_question_ids(self, user_id: str) -> List[str]:
        with self._get_connection() as conn:
            logger.debug(f"🔍 DB: Querying incorrect answers for {user_id}")
            cursor = conn.execute(
                "SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0",
                (user_id,)
            )
            ids = [row[0] for row in cursor.fetchall()]

            # Forensic Type Check
            if ids:
                logger.debug(f"🕵️‍♂️ TYPE CHECK (DB): Found {len(ids)} IDs. Sample: '{ids[0]}' (Type: {type(ids[0])})")

            return ids

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool):
        """
        Records a raw attempt.
        Does NOT handle profile stats updates (Separation of Concerns).
        """
        logger.debug(f"💾 DB WRITE: Inserting/Updating attempt for {user_id} on {question_id}")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_progress (user_id, question_id, is_correct)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_id) 
                DO UPDATE SET is_correct=excluded.is_correct, timestamp=CURRENT_TIMESTAMP
            """, (user_id, question_id, is_correct))
            conn.commit()
        logger.debug("💾 DB: Save committed.")

    def reset_user_progress(self, user_id: str):
        logger.warning(f"🧨 DB: Wiping all history for {user_id}")
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
            conn.execute("""
                UPDATE user_profiles 
                SET streak_days=0, daily_progress=0 
                WHERE user_id = ?
            """, (user_id,))

    # --- User Profile Management ---

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        logger.debug(f"👤 DB: Fetching profile for {user_id}")
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            today = date.today()

            if not row:
                logger.info(f"👤 DB: Creating NEW profile for {user_id}")
                profile = UserProfile(user_id=user_id)
                conn.execute("""
                    INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress, last_daily_reset)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (profile.user_id, profile.streak_days, today, profile.daily_goal, 0, today))
                return profile

            # Map DB row to Pydantic
            return UserProfile(
                user_id=row[0],
                streak_days=row[1],
                last_login=datetime.strptime(row[2], "%Y-%m-%d").date() if row[2] else today,
                daily_goal=row[3],
                daily_progress=row[4],
                last_daily_reset=datetime.strptime(row[5], "%Y-%m-%d").date() if row[5] else today
            )

    def save_profile(self, profile: UserProfile):
        """
        Persists the UserProfile state.
        The Service is responsible for calculating the values inside 'profile'.
        """
        logger.debug(f"💾 DB WRITE: Updating profile for {profile.user_id}. Streak={profile.streak_days}, Progress={profile.daily_progress}")
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

    # --- Debug / Forensics ---

    def debug_get_user_stats(self, user_id: str) -> dict:
        """
        Returns raw statistics for debugging UI.
        """
        with self._get_connection() as conn:
            total = conn.execute("SELECT count(*) FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()[0]
            correct = conn.execute("SELECT count(*) FROM user_progress WHERE user_id = ? AND is_correct = 1",
                                   (user_id,)).fetchone()[0]
            incorrect = conn.execute("SELECT count(*) FROM user_progress WHERE user_id = ? AND is_correct = 0",
                                     (user_id,)).fetchone()[0]

            incorrect_ids = [row[0] for row in
                             conn.execute("SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0",
                                          (user_id,)).fetchall()]

            return {
                "total_attempts": total,
                "correct_count": correct,
                "incorrect_count": incorrect,
                "incorrect_ids": incorrect_ids
            }