import json
import os
import random
import sqlite3
from datetime import date, datetime

from src.config import GameConfig
from src.quiz.domain.models import Question, UserProfile
from src.quiz.domain.ports import IQuizRepository
from src.shared.telemetry import Telemetry, measure_time


class SQLiteQuizRepository(IQuizRepository):
    def __init__(self, db_path: str = "data/quiz.db", auto_seed: bool = True) -> None:
        self.telemetry = Telemetry("SQLiteRepository")
        self.db_path = db_path
        # Fix: Type hint as Optional[sqlite3.Connection] instead of Any
        self._shared_connection: sqlite3.Connection | None = None
        self._ensure_db_exists()
        if self.db_path == ":memory:":
            self._shared_connection = sqlite3.connect(
                ":memory:", check_same_thread=False
            )
        self._init_schema()
        self._migrate_schema()

        if auto_seed:
            self._seed_if_empty()

    def _ensure_db_exists(self) -> None:
        if self.db_path == ":memory:":
            return
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_connection:
            return self._shared_connection
        return sqlite3.connect(self.db_path)

    def close(self) -> None:
        if self._shared_connection:
            self._shared_connection.close()

    @measure_time("db_init_schema")
    def _init_schema(self) -> None:
        conn = self._get_connection()
        try:
            # Questions Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS questions (
                    id TEXT PRIMARY KEY,
                    category TEXT,
                    json_data TEXT
                )
                """
            )

            # User Progress Table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id TEXT,
                    question_id TEXT,
                    is_correct BOOLEAN,
                    consecutive_correct INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, question_id)
                )
                """
            )

            # User Profiles
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    streak_days INTEGER DEFAULT 0,
                    last_login DATE,
                    daily_goal INTEGER DEFAULT 3,
                    daily_progress INTEGER DEFAULT 0,
                    last_daily_reset DATE,
                    has_completed_onboarding BOOLEAN DEFAULT 0
                )
                """
            )
            conn.commit()
        except Exception as e:
            self.telemetry.log_error("Schema Init Failed", e)

    def _migrate_schema(self) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.execute("PRAGMA table_info(user_progress)")
            columns = [row[1] for row in cursor.fetchall()]

            if "consecutive_correct" not in columns:
                self.telemetry.log_info(
                    "Migrating DB: Adding consecutive_correct column"
                )
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
        except Exception as e:
            self.telemetry.log_error("Migration Failed", e)

    def _seed_if_empty(self) -> None:
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT count(*) FROM questions")
            result = cursor.fetchone()
            count = result[0] if result else 0

            if count == 0:
                self.telemetry.log_info("DB is empty. Attempting to seed...")
                seed_file = "data/seed_questions.json"
                if os.path.exists(seed_file):
                    with open(seed_file, encoding="utf-8") as f:
                        data = json.load(f)
                        questions = [Question(**q) for q in data]
                        self.seed_questions(questions)
                else:
                    self.telemetry.log_error(
                        "Seed file NOT found", Exception(f"Missing: {seed_file}")
                    )
        except Exception as e:
            self.telemetry.log_error("Auto-seeding failed", e)

    @measure_time("db_get_all_questions")
    def get_all_questions(self) -> list[Question]:
        try:
            conn = self._get_connection()
            cursor = conn.execute("SELECT json_data FROM questions")
            results = [
                Question.model_validate_json(row[0]) for row in cursor.fetchall()
            ]
            return results
        except Exception as e:
            self.telemetry.log_error("get_all_questions failed", e)
            return []

    def get_questions_by_ids(self, question_ids: list[str]) -> list[Question]:
        if not question_ids:
            return []
        placeholders = ",".join(["?"] * len(question_ids))
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                f"SELECT json_data FROM questions WHERE id IN ({placeholders})",
                question_ids,
            )
            return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            self.telemetry.log_error("get_questions_by_ids failed", e)
            return []

    def seed_questions(self, questions: list[Question]) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            for q in questions:
                cursor.execute(
                    "INSERT OR REPLACE INTO questions (id, json_data, category) "
                    "VALUES (?, ?, ?)",
                    (q.id, q.json(), q.category),
                )
            conn.commit()
        except sqlite3.Error as e:
            self.telemetry.log_error("seed_questions failed", e)

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        )
        row = cursor.fetchone()
        today = date.today()

        if not row:
            profile = UserProfile(user_id=user_id)
            conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, streak_days, last_login, daily_goal,
                    daily_progress, last_daily_reset, has_completed_onboarding
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.user_id,
                    profile.streak_days,
                    today,
                    profile.daily_goal,
                    0,
                    today,
                    False,
                ),
            )
            conn.commit()
            return profile

        has_onboarding = False
        if len(row) > 6:
            has_onboarding = bool(row[6])

        return UserProfile(
            user_id=row[0],
            streak_days=row[1],
            last_login=datetime.strptime(row[2], "%Y-%m-%d").date()
            if row[2]
            else today,
            daily_goal=row[3],
            daily_progress=row[4],
            last_daily_reset=datetime.strptime(row[5], "%Y-%m-%d").date()
            if row[5]
            else today,
            has_completed_onboarding=has_onboarding,
        )

    def save_profile(self, profile: UserProfile) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            UPDATE user_profiles
            SET streak_days = ?, last_login = ?, daily_goal = ?,
                daily_progress = ?, last_daily_reset = ?, has_completed_onboarding = ?
            WHERE user_id = ?
            """,
            (
                profile.streak_days,
                profile.last_login,
                profile.daily_goal,
                profile.daily_progress,
                profile.last_daily_reset,
                profile.has_completed_onboarding,
                profile.user_id,
            ),
        )
        conn.commit()

    def was_question_answered_on_date(
        self, user_id: str, question_id: str, check_date: date
    ) -> bool:
        date_str = check_date.strftime("%Y-%m-%d")
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT count(*) FROM user_progress
            WHERE user_id = ? AND question_id = ? AND date(timestamp) = ?
            """,
            (user_id, question_id, date_str),
        )
        result = cursor.fetchone()
        return bool(result[0] > 0) if result else False

    def get_incorrect_question_ids(self, user_id: str) -> list[str]:
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT question_id FROM user_progress
            WHERE user_id = ? AND is_correct = 0
            """,
            (user_id,),
        )
        return [row[0] for row in cursor.fetchall()]

    def get_all_attempted_ids(self, user_id: str) -> list[str]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT question_id FROM user_progress WHERE user_id = ?", (user_id,)
        )
        return [row[0] for row in cursor.fetchall()]

    def reset_user_progress(self, user_id: str) -> None:
        conn = self._get_connection()
        conn.execute("DELETE FROM user_progress WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            UPDATE user_profiles
            SET streak_days=0, daily_progress=0, has_completed_onboarding=0
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool) -> None:
        conn = self._get_connection()
        sql = """
            INSERT INTO user_progress (
                user_id, question_id, is_correct, consecutive_correct, timestamp
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, question_id)
            DO UPDATE SET
                consecutive_correct = CASE
                    WHEN excluded.is_correct = 1
                    THEN user_progress.consecutive_correct + 1
                    ELSE 0
                END,
                is_correct = excluded.is_correct,
                timestamp = CURRENT_TIMESTAMP
        """
        initial_streak = 1 if is_correct else 0
        conn.execute(sql, (user_id, question_id, is_correct, initial_streak))
        conn.commit()

    @measure_time("db_get_smart_mix")
    def get_smart_mix(self, user_id: str, limit: int = 15) -> list[Question]:
        conn = self._get_connection()
        query = """
            SELECT q.json_data,
                   COALESCE(up.consecutive_correct, 0) as streak,
                   up.question_id IS NOT NULL          as seen
            FROM questions q
            LEFT JOIN user_progress up
                ON q.id = up.question_id AND up.user_id = ?
        """
        cursor = conn.execute(query, (user_id,))
        rows = cursor.fetchall()

        learning_pool = []
        unseen_pool = []

        for row in rows:
            q_json, streak, seen = row
            if streak >= GameConfig.MASTERY_THRESHOLD:
                continue

            q = Question.model_validate_json(q_json)

            if not seen or streak < GameConfig.MASTERY_THRESHOLD:
                if seen:
                    learning_pool.append(q)
                else:
                    unseen_pool.append(q)

        target_new = int(limit * GameConfig.NEW_RATIO)
        target_review = limit - target_new

        random.shuffle(learning_pool)
        random.shuffle(unseen_pool)

        selected = []
        selected.extend(learning_pool[:target_review])
        selected.extend(unseen_pool[:target_new])

        if len(selected) < limit:
            needed = limit - len(selected)
            remaining_new = unseen_pool[target_new:]
            selected.extend(remaining_new[:needed])

        if len(selected) < limit:
            needed = limit - len(selected)
            remaining_learning = learning_pool[target_review:]
            selected.extend(remaining_learning[:needed])

        random.shuffle(selected)
        self.telemetry.log_info(f"Smart Mix Generated: {len(selected)} questions")
        return selected[:limit]

    def get_questions_by_category(
        self, category: str, user_id: str, limit: int = 15
    ) -> list[Question]:
        conn = self._get_connection()
        query = """
            SELECT q.json_data
            FROM questions q
            LEFT JOIN user_progress up
                ON q.id = up.question_id AND up.user_id = ?
            WHERE q.category = ?
            ORDER BY COALESCE(up.consecutive_correct, 0) ASC, RANDOM()
            LIMIT ?
        """
        cursor = conn.execute(query, (user_id, category, limit))
        return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
