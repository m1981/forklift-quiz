import sqlite3
from datetime import date, datetime
from typing import Any

from src.config import GameConfig
from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.domain.category_selector import CategorySelector
from src.quiz.domain.models import Language, Question, QuestionCandidate, UserProfile
from src.quiz.domain.ports import IQuizRepository
from src.shared.telemetry import Telemetry, measure_time


class SQLiteQuizRepository(IQuizRepository):
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.telemetry = Telemetry("SQLiteRepository")
        self.db_manager = db_manager

    def _get_connection(self) -> sqlite3.Connection:
        return self.db_manager.get_connection()

    def is_empty(self) -> bool:
        """Helper for the Seeder."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT count(*) FROM questions")
        result = cursor.fetchone()
        count = result[0] if result else 0
        if not self.db_manager._shared_connection:
            conn.close()
        return count == 0

    @measure_time("db_get_repetition_candidates")
    def get_repetition_candidates(self, user_id: str) -> list[QuestionCandidate]:
        conn = self._get_connection()
        threshold = GameConfig.MASTERY_THRESHOLD

        query = """
                SELECT q.json_data,
                       COALESCE(up.consecutive_correct, 0) as streak,
                       up.question_id IS NOT NULL          as seen
                FROM questions q
                         LEFT JOIN user_progress up
                                   ON q.id = up.question_id AND up.user_id = ?
                WHERE up.question_id IS NULL
                   OR up.consecutive_correct < ?
                   OR (up.consecutive_correct >= ?
                           AND up.timestamp < date ('now', '-3 days') \
                    ) \
                """
        cursor = conn.execute(query, (user_id, threshold, threshold))

        candidates = []
        for row in cursor.fetchall():
            q_json, streak, seen = row
            q = Question.model_validate_json(q_json)
            candidates.append(
                QuestionCandidate(question=q, streak=streak, is_seen=bool(seen))
            )

        if not self.db_manager._shared_connection:
            conn.close()

        return candidates

    @measure_time("db_get_category_stats")
    def get_category_stats(self, user_id: str) -> list[dict[str, int | str]]:
        conn = self._get_connection()
        threshold = GameConfig.MASTERY_THRESHOLD

        self.telemetry.log_info(
            f"Calculating stats for user={user_id} with threshold={threshold}"
        )

        sql = """
              SELECT q.category,
                     COUNT(q.id) as total,
                     SUM(CASE
                             WHEN COALESCE(up.consecutive_correct, 0) >= ?
                                 THEN 1
                             ELSE 0
                         END)    as mastered
              FROM questions q
                       LEFT JOIN user_progress up
                                 ON q.id = up.question_id AND up.user_id = ?
              GROUP BY q.category \
              """

        cursor = conn.execute(sql, (threshold, user_id))

        stats = []
        raw_rows = cursor.fetchall()

        for row in raw_rows:
            stats.append(
                {
                    "category": row[0],
                    "total": row[1],
                    "mastered": row[2] if row[2] else 0,
                }
            )

        if not self.db_manager._shared_connection:
            conn.close()
        return stats

    def get_questions_by_ids(self, question_ids: list[str]) -> list[Question]:
        if not question_ids:
            return []
        placeholders = ",".join(["?"] * len(question_ids))
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT json_data FROM questions WHERE id IN ({placeholders})",
                question_ids,
            )
            return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
        except Exception as e:
            self.telemetry.log_error("get_questions_by_ids failed", e)
            return []
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def seed_questions(self, questions: list[Question]) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            for q in questions:
                cursor.execute(
                    "INSERT OR REPLACE INTO questions (id, json_data, category) "
                    "VALUES (?, ?, ?)",
                    (q.id, q.model_dump_json(), q.category),
                )
            conn.commit()
        except sqlite3.Error as e:
            self.telemetry.log_error("seed_questions failed", e)
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def get_or_create_profile(self, user_id: str) -> UserProfile:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            today = date.today()

            if not row:
                # --- FIX 1: Create new profile logic ---
                profile = UserProfile(
                    user_id=user_id,
                    streak_days=1,
                    last_login=today,
                    last_daily_reset=today,
                    preferred_language=Language.PL,
                    demo_prospect_slug=None,
                    has_completed_onboarding=False,
                )
                conn.execute(
                    """
                    INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal,
                                               daily_progress, last_daily_reset,
                                               has_completed_onboarding, preferred_language,
                                               demo_prospect_slug)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.user_id,
                        profile.streak_days,
                        today.isoformat(),
                        profile.daily_goal,
                        0,
                        today.isoformat(),
                        False,
                        profile.preferred_language.value,
                        None,
                    ),
                )
                conn.commit()
                return profile
                # ---------------------------------------

            # --- FIX 2: Robust Row Parsing ---
            # We map columns by index, assuming the order from SELECT *
            # 0: user_id, 1: streak_days, 2: last_login, 3: daily_goal,
            # 4: daily_progress, 5: last_daily_reset, 6: has_completed_onboarding
            # 7: preferred_language, 8: demo_prospect_slug

            # Helper to safely get column if it exists (migration safety)
            def get_col(idx: int, default: Any = None) -> Any:
                return row[idx] if len(row) > idx else default

            profile = UserProfile(
                user_id=row[0],
                streak_days=row[1],
                last_login=today,  # Will be updated below if needed
                daily_goal=row[3],
                daily_progress=row[4],
                last_daily_reset=datetime.strptime(row[5], "%Y-%m-%d").date()
                if row[5]
                else today,
                has_completed_onboarding=bool(row[6]),
                preferred_language=Language(get_col(7)) if get_col(7) else Language.PL,
                demo_prospect_slug=get_col(8),
            )

            # Streak Logic
            last_login_db = (
                datetime.strptime(row[2], "%Y-%m-%d").date() if row[2] else today
            )
            delta = (today - last_login_db).days

            if delta == 1:
                profile.streak_days += 1
                profile.last_login = today
            elif delta > 1 or delta < 0:
                profile.streak_days = 1
                profile.last_login = today

            # Only save if changed (delta > 0 means date changed)
            if delta > 0:
                self.save_profile(profile)

            return profile
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def save_profile(self, profile: UserProfile) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE user_profiles
                SET streak_days              = ?,
                    last_login               = ?,
                    daily_goal               = ?,
                    daily_progress           = ?,
                    last_daily_reset         = ?,
                    has_completed_onboarding = ?,
                    preferred_language       = ?,
                    demo_prospect_slug       = ?
                WHERE user_id = ?
                """,
                (
                    profile.streak_days,
                    profile.last_login.isoformat(),
                    profile.daily_goal,
                    profile.daily_progress,
                    profile.last_daily_reset.isoformat(),
                    profile.has_completed_onboarding,
                    profile.preferred_language.value,
                    profile.demo_prospect_slug,
                    profile.user_id,
                ),
            )
            conn.commit()
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    @measure_time("db_save_attempt")
    def save_attempt(self, user_id: str, question_id: str, is_correct: bool) -> None:
        conn = self._get_connection()
        try:
            is_correct_int = 1 if is_correct else 0
            initial_streak = 1 if is_correct else 0

            # --- FIX 3: Simplified UPSERT Logic ---
            # We use COALESCE to ensure we don't add to NULL
            sql = """
                  INSERT INTO user_progress (user_id, question_id, is_correct, \
                                             consecutive_correct, timestamp)
                  VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP) ON CONFLICT(user_id, question_id)
                DO \
                  UPDATE SET
                      consecutive_correct = CASE \
                      WHEN excluded.is_correct = 1 \
                      THEN COALESCE (user_progress.consecutive_correct, 0) + 1 \
                      ELSE 0
                  END \
                  ,
                  is_correct = excluded.is_correct,
                  timestamp = CURRENT_TIMESTAMP
                  """

            conn.execute(sql, (user_id, question_id, is_correct_int, initial_streak))
            conn.commit()
        except Exception as e:
            self.telemetry.log_error(f"save_attempt failed for {user_id}", e)
            raise e
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def get_questions_by_category(
        self, category: str, user_id: str, limit: int = GameConfig.SPRINT_QUESTIONS
    ) -> list[Question]:
        conn = self._get_connection()
        try:
            query = """
                    SELECT q.json_data, COALESCE(up.consecutive_correct, 0) as streak
                    FROM questions q
                             LEFT JOIN user_progress up
                                       ON q.id = up.question_id AND up.user_id = ?
                    WHERE q.category = ? \
                    """

            # Fetch all matching category questions first
            rows = conn.execute(query, (user_id, category)).fetchall()

            # Convert to candidates
            candidates = [
                (Question.model_validate_json(row[0]), row[1]) for row in rows
            ]

            # Use Domain Logic to sort and limit
            return CategorySelector.prioritize_weak_questions(candidates, limit)
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    @measure_time("db_get_mastery")
    def get_mastery_percentage(self, user_id: str, category: str) -> float:
        conn = self._get_connection()
        threshold = GameConfig.MASTERY_THRESHOLD
        try:
            sql = """
                  SELECT COUNT(q.id) as total, \
                         SUM(CASE \
                                 WHEN COALESCE(up.consecutive_correct, 0) >= ? \
                                     THEN 1 \
                                 ELSE 0 \
                             END)    as mastered
                  FROM questions q
                           LEFT JOIN user_progress up
                                     ON q.id = up.question_id AND up.user_id = ?
                  WHERE q.category = ? \
                  """
            cursor = conn.execute(sql, (threshold, user_id, category))
            row = cursor.fetchone()

            if not row or row[0] == 0:
                return 0.0
            return float(row[1]) / float(row[0])
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def debug_dump_user_progress(self, user_id: str) -> list[dict[str, Any]]:
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT question_id, is_correct, consecutive_correct, timestamp
                FROM user_progress
                WHERE user_id = ?
                ORDER BY timestamp DESC
                    LIMIT 20
                """,
                (user_id,),
            )
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
        finally:
            if not self.db_manager._shared_connection:
                conn.close()
