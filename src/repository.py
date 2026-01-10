import sqlite3
import logging
import os
from datetime import date, datetime, timedelta
from typing import List, Optional
from src.models import Question, UserProfile

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
        logger.debug("🔍 DB: Checking schema...")
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
            # 3. NEW: User Profiles Table
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

    def get_all_attempted_ids(self, user_id: str) -> List[str]:
        """Returns IDs of ALL questions the user has ever answered (Correct or Incorrect)."""
        with self._get_connection() as conn:
            logger.debug(f"🔍 DB: Fetching attempted IDs for user='{user_id}'")
            cursor = conn.execute(
                "SELECT question_id FROM user_progress WHERE user_id = ?",
                (user_id,)
            )
            results = [row[0] for row in cursor.fetchall()]
            logger.debug(f"🔍 DB: Found {len(results)} attempted questions.")
            return results

    # --- Existing Question Methods (Unchanged) ---
    def seed_questions(self, questions: List[Question]):
        # ... (Keep your existing smart seeding logic here) ...
        # For brevity, I am not repeating the full smart seeding code,
        # but ensure you keep the version we wrote previously!
        try:
            existing_questions = {q.id: q for q in self.get_all_questions()}
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for new_q in questions:
                    old_q = existing_questions.get(new_q.id)
                    if old_q and old_q.correct_option != new_q.correct_option:
                        cursor.execute("DELETE FROM user_progress WHERE question_id = ?", (new_q.id,))
                    cursor.execute("INSERT OR REPLACE INTO questions (id, json_data) VALUES (?, ?)", (new_q.id, new_q.json()))
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to seed questions: {e}")

    def get_all_questions(self) -> List[Question]:
        try:
            with self._get_connection() as conn:
                logger.debug("🔍 DB: Fetching ALL questions from 'questions' table.")
                cursor = conn.execute("SELECT json_data FROM questions")
                rows = cursor.fetchall()
                questions = [Question.model_validate_json(row[0]) for row in rows]
                logger.debug(f"🔍 DB: Successfully deserialized {len(questions)} questions.")
                return questions
        except Exception as e:
            logger.error(f"❌ DB ERROR: Fetching questions failed: {e}", exc_info=True)
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
        logger.info(f"💾 DB: Saving Attempt -> User={user_id}, Q={question_id}, Correct={is_correct}")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_progress (user_id, question_id, is_correct)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_id) 
                DO UPDATE SET is_correct=excluded.is_correct, timestamp=CURRENT_TIMESTAMP
            """, (user_id, question_id, is_correct))
            conn.commit()
        logger.debug("💾 DB: Save committed.")

    def get_incorrect_question_ids(self, user_id: str) -> List[str]:
        with self._get_connection() as conn:
            logger.debug(f"🔍 DB: Querying incorrect answers for {user_id}")
            cursor = conn.execute(
                "SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0",
                (user_id,)
            )
            ids = [row[0] for row in cursor.fetchall()]
            logger.info(f"📉 DB: User {user_id} has {len(ids)} active errors: {ids}")
            return ids

    def reset_user_progress(self, user_id: str):
        logger.warning(f"🧨 DB: Wiping all history for {user_id}")
        with self._get_connection() as conn:
            conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
            # Also reset profile stats
            conn.execute("""
                UPDATE user_profiles 
                SET streak_days=0, daily_progress=0 
                WHERE user_id = ?
            """, (user_id,))

    # --- NEW: User Profile Methods ---

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        logger.debug(f"👤 DB: Fetching profile for {user_id}")
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

            today = date.today()

            if not row:
                logger.info(f"👤 DB: No profile found for {user_id}. Creating new.")
                profile = UserProfile(user_id=user_id)
                conn.execute("""
                    INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress, last_daily_reset)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (profile.user_id, profile.streak_days, today, profile.daily_goal, 0, today))
                return profile

            # Parse existing profile
            # Row order: user_id, streak_days, last_login, daily_goal, daily_progress, last_daily_reset
            streak = row[1]
            last_login_str = row[2]
            daily_goal = row[3]
            daily_progress = row[4]
            last_reset_str = row[5]

            # --- TRACE LOGGING FOR PROFILE DATA ---
            logger.debug(f"👤 DB: Raw Profile Row for '{user_id}': Goal={daily_goal}, Progress={daily_progress}")
            # --------------------------------------

            last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date() if last_login_str else today
            last_reset = datetime.strptime(last_reset_str, "%Y-%m-%d").date() if last_reset_str else today

            if last_reset < today:
                logger.warning(f"📅 DB: New Day Detected! Resetting daily progress for {user_id}. (Last: {last_reset}, Today: {today})")
                daily_progress = 0
                last_reset = today
                conn.execute("""
                    UPDATE user_profiles 
                    SET daily_progress = 0, last_daily_reset = ? 
                    WHERE user_id = ?
                """, (today, user_id))
            else:
                logger.debug(f"📅 DB: No rollover needed. Last reset: {last_reset}, Today: {today}")

            return UserProfile(
                user_id=user_id,
                streak_days=streak,
                last_login=last_login,
                daily_goal=daily_goal,
                daily_progress=daily_progress,
                last_daily_reset=last_reset
            )

    def update_profile_stats(self, user_id: str, increment_progress: bool = True):
        profile = self.get_or_create_profile(user_id)
        today = date.today()

        new_streak = profile.streak_days
        if profile.last_login == today - timedelta(days=1):
            new_streak += 1
        elif profile.last_login < today - timedelta(days=1):
            if profile.streak_days > 0:
                new_streak = 1
            else:
                new_streak = 1
        elif profile.last_login == today:
            if new_streak == 0: new_streak = 1

        new_progress = profile.daily_progress + (1 if increment_progress else 0)

        logger.info(f"📈 DB: Stats Updated for {user_id}. Streak={new_streak}, Daily={new_progress}")

        with self._get_connection() as conn:
            conn.execute("""
                UPDATE user_profiles 
                SET streak_days = ?, last_login = ?, daily_progress = ?
                WHERE user_id = ?
            """, (new_streak, today, new_progress, user_id))

    def debug_dump_user_state(self, user_id: str):
        """
        DEBUG TOOL: Prints raw DB state to console for verification.
        """
        with self._get_connection() as conn:
            print(f"\n--- 🕵️‍♂️ DEBUG DUMP FOR {user_id} ---")

            # 1. Check Profile
            row = conn.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)).fetchone()
            print(f"👤 PROFILE: {row}")

            # 2. Check Incorrect Answers (The 'Review' Queue)
            cursor = conn.execute("SELECT question_id FROM user_progress WHERE user_id = ? AND is_correct = 0",
                                  (user_id,))
            incorrect = [r[0] for r in cursor.fetchall()]
            print(f"❌ INCORRECT IDs ({len(incorrect)}): {incorrect}")

            # 3. Check Total Daily Activity
            # We count how many records have today's timestamp (approximate check)
            cursor = conn.execute(
                "SELECT count(*) FROM user_progress WHERE user_id = ? AND date(timestamp) = date('now')", (user_id,))
            today_count = cursor.fetchone()[0]
            print(f"📅 ANSWERS TODAY (DB Count): {today_count}")
            print("-------------------------------------\n")