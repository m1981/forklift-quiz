import sqlite3
from datetime import date, datetime
from typing import Any

from src.config import GameConfig
from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.domain.models import Question, QuestionCandidate, UserProfile
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
        cursor = conn.execute(
            query, (user_id, GameConfig.MASTERY_THRESHOLD, GameConfig.MASTERY_THRESHOLD)
        )

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

    def get_category_stats(self, user_id: str) -> list[dict[str, int | str]]:
        conn = self._get_connection()
        sql = """
              SELECT q.category,
                     COUNT(q.id) as total,
                     SUM(CASE
                             WHEN COALESCE(up.consecutive_correct, 0) >= 3
                                 THEN 1
                             ELSE 0
                         END)    as mastered
              FROM questions q
                       LEFT JOIN user_progress up
                                 ON q.id = up.question_id AND up.user_id = ?
              GROUP BY q.category \
              """
        cursor = conn.execute(sql, (user_id,))
        stats = []
        for row in cursor.fetchall():
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
                    (q.id, q.json(), q.category),
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
                profile = UserProfile(
                    user_id=user_id,
                    streak_days=1,
                    last_login=today,
                    last_daily_reset=today,
                )
                conn.execute(
                    """
                    INSERT INTO user_profiles (
                        user_id, streak_days, last_login, daily_goal,
                        daily_progress, last_daily_reset,
                        has_completed_onboarding
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

            # Existing User Logic
            last_login_db = (
                datetime.strptime(row[2], "%Y-%m-%d").date() if row[2] else today
            )
            current_streak = row[1]
            delta = (today - last_login_db).days
            new_streak = current_streak

            if delta == 1:
                new_streak += 1
            elif delta > 1:
                new_streak = 1

            profile = UserProfile(
                user_id=row[0],
                streak_days=new_streak,
                last_login=today,
                daily_goal=row[3],
                daily_progress=row[4],
                last_daily_reset=datetime.strptime(row[5], "%Y-%m-%d").date()
                if row[5]
                else today,
                has_completed_onboarding=bool(row[6]) if len(row) > 6 else False,
            )

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
                    has_completed_onboarding = ?
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
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def save_attempt(self, user_id: str, question_id: str, is_correct: bool) -> None:
        conn = self._get_connection()
        try:
            sql = """
                  INSERT INTO user_progress (
                      user_id, question_id, is_correct,
                      consecutive_correct, timestamp
                  )
                  VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                  ON CONFLICT(user_id, question_id)
                DO \
                  UPDATE SET
                      consecutive_correct = CASE \
                      WHEN excluded.is_correct = 1 \
                      THEN user_progress.consecutive_correct + 1 \
                      ELSE 0
                  END \
                  ,
                    is_correct = excluded.is_correct,
                    timestamp = CURRENT_TIMESTAMP \
                  """
            initial_streak = 1 if is_correct else 0
            conn.execute(sql, (user_id, question_id, is_correct, initial_streak))
            conn.commit()
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def get_questions_by_category(
        self, category: str, user_id: str, limit: int = 15
    ) -> list[Question]:
        conn = self._get_connection()
        try:
            query = """
                    SELECT q.json_data
                    FROM questions q
                             LEFT JOIN user_progress up
                                       ON q.id = up.question_id AND up.user_id = ?
                    WHERE q.category = ?
                    ORDER BY COALESCE(up.consecutive_correct, 0) ASC, RANDOM() LIMIT ? \
                    """
            cursor = conn.execute(query, (user_id, category, limit))
            return [Question.model_validate_json(row[0]) for row in cursor.fetchall()]
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    def get_mastery_percentage(self, user_id: str, category: str) -> float:
        conn = self._get_connection()
        try:
            sql = """
                  SELECT COUNT(q.id) as total, \
                         SUM(CASE \
                                 WHEN COALESCE(up.consecutive_correct, 0) >= 3 \
                                     THEN 1 \
                                 ELSE 0 \
                             END)    as mastered
                  FROM questions q
                           LEFT JOIN user_progress up
                                     ON q.id = up.question_id AND up.user_id = ?
                  WHERE q.category = ? \
                  """
            cursor = conn.execute(sql, (user_id, category))
            row = cursor.fetchone()
            if not row or row[0] == 0:
                return 0.0
            return float(row[1]) / float(row[0])
        finally:
            if not self.db_manager._shared_connection:
                conn.close()

    # --- ADR 006: Debug Methods in Repository ---
    # Decision: We allow `debug_dump_user_progress` in the concrete
    # implementation.
    # Rationale: This method is used by the `app.py` entry point for
    # developer diagnostics. It is NOT part of the `IQuizRepository`
    # interface because domain logic should not rely on raw debug dumps.
    # It is strictly for the outer shell (Infrastructure/Main).
    # --------------------------------------------
    def debug_dump_user_progress(self, user_id: str) -> list[dict[str, Any]]:
        """
        Returns raw rows from user_progress for debugging.
        """
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
