from datetime import date, datetime
from typing import Any, cast

from postgrest.types import CountMethod

from src.config import GameConfig
from src.quiz.domain.category_selector import CategorySelector
from src.quiz.domain.models import Question, QuestionCandidate, UserProfile
from src.quiz.domain.ports import IQuizRepository
from src.shared.telemetry import Telemetry, measure_time
from supabase import Client, create_client


class SupabaseQuizRepository(IQuizRepository):
    def __init__(self, url: str, key: str) -> None:
        self.telemetry = Telemetry("SupabaseRepository")
        try:
            self.client: Client = create_client(url, key)
        except Exception as e:
            self.telemetry.log_error("Failed to initialize Supabase client", e)
            raise

    def is_empty(self) -> bool:
        """
        Used by DataSeeder to check if we need to parse the JSON and upload.
        """
        try:
            response = (
                self.client.table("questions")
                .select("id", count=cast(CountMethod, "exact"))
                .limit(1)
                .execute()
            )
            return (response.count or 0) == 0
        except Exception as e:
            self.telemetry.log_error("is_empty check failed", e)
            return True

    def seed_questions(self, questions: list[Question]) -> None:
        """
        Parses the list of Questions (from JSON) and upserts them to Supabase.
        """
        try:
            # Prepare batch data
            data: list[dict[str, Any]] = [
                {
                    "id": q.id,
                    "category": q.category,
                    "json_data": q.model_dump(mode="json"),
                }
                for q in questions
            ]

            # Upsert in chunks of 100 to prevent payload size issues
            chunk_size = 100
            for i in range(0, len(data), chunk_size):
                chunk = data[i : i + chunk_size]
                self.client.table("questions").upsert(chunk).execute()

            self.telemetry.log_info(f"Seeded {len(questions)} questions to Supabase")
        except Exception as e:
            self.telemetry.log_error("seed_questions failed", e)

    @measure_time("sb_get_questions_by_ids")
    def get_questions_by_ids(self, question_ids: list[str]) -> list[Question]:
        if not question_ids:
            return []
        try:
            response = (
                self.client.table("questions")
                .select("json_data")
                .in_("id", question_ids)
                .execute()
            )
            data = cast(list[dict[str, Any]], response.data)
            return [Question.model_validate(row["json_data"]) for row in data]
        except Exception as e:
            self.telemetry.log_error("get_questions_by_ids failed", e)
            return []

    @measure_time("sb_get_profile")
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        try:
            response = (
                self.client.table("user_profiles")
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )

            today = date.today()
            data = cast(list[dict[str, Any]], response.data)

            if not data:
                # Create new profile
                new_profile = UserProfile(
                    user_id=user_id,
                    streak_days=1,
                    last_login=today,
                    last_daily_reset=today,
                    metadata={},
                    demo_prospect_slug=None,
                )
                payload = new_profile.model_dump(mode="json")
                self.client.table("user_profiles").insert(payload).execute()
                return new_profile

            # Existing User Logic
            row = data[0]
            last_login_db = datetime.strptime(str(row["last_login"]), "%Y-%m-%d").date()
            current_streak = int(row["streak_days"])
            delta = (today - last_login_db).days

            new_streak = current_streak
            if delta == 1:
                new_streak += 1
            elif delta > 1 or delta < 0:
                new_streak = 1

            profile = UserProfile(
                user_id=str(row["user_id"]),
                streak_days=new_streak,
                last_login=today,
                daily_goal=int(row["daily_goal"]),
                daily_progress=int(row["daily_progress"]),
                last_daily_reset=datetime.strptime(
                    str(row["last_daily_reset"]), "%Y-%m-%d"
                ).date(),
                has_completed_onboarding=bool(row["has_completed_onboarding"]),
                metadata=row.get("metadata", {}),
                demo_prospect_slug=row.get("demo_prospect_slug"),
            )

            if delta > 0:
                self.save_profile(profile)

            return profile
        except Exception as e:
            self.telemetry.log_error(f"get_or_create_profile failed for {user_id}", e)
            return UserProfile(user_id=user_id)

    def save_profile(
        self, profile: UserProfile, fields: set[str] | None = None
    ) -> None:
        """
        Save profile to database.

        Args:
            profile: The profile to save
            fields: Optional set of field names to update. If None, updates all fields.
        """
        # Build payload with only specified fields
        if fields:
            payload: dict[str, Any] = {}
            field_mapping: dict[str, Any] = {
                "streak_days": profile.streak_days,
                "last_login": str(profile.last_login),
                "daily_goal": profile.daily_goal,
                "daily_progress": profile.daily_progress,
                "last_daily_reset": str(profile.last_daily_reset),
                "preferred_language": profile.preferred_language.value,
                "has_completed_onboarding": profile.has_completed_onboarding,
                "metadata": profile.metadata,
                "demo_prospect_slug": profile.demo_prospect_slug,
            }
            for field in fields:
                if field in field_mapping:
                    payload[field] = field_mapping[field]
        else:
            # Full update (existing behavior)
            payload = {
                "streak_days": profile.streak_days,
                "last_login": str(profile.last_login),
                "daily_goal": profile.daily_goal,
                "daily_progress": profile.daily_progress,
                "last_daily_reset": str(profile.last_daily_reset),
                "preferred_language": profile.preferred_language.value,
                "has_completed_onboarding": profile.has_completed_onboarding,
                "metadata": profile.metadata,
                "demo_prospect_slug": profile.demo_prospect_slug,
            }

        self.client.table("user_profiles").update(payload).eq(
            "user_id", profile.user_id
        ).execute()

    @measure_time("sb_save_attempt")
    def save_attempt(self, user_id: str, question_id: str, is_correct: bool) -> None:
        try:
            self.client.rpc(
                "submit_attempt",
                {
                    "p_user_id": user_id,
                    "p_question_id": question_id,
                    "p_is_correct": is_correct,
                },
            ).execute()
        except Exception as e:
            self.telemetry.log_error(f"save_attempt failed for {user_id}", e)
            raise e

    @measure_time("sb_get_mastery")
    def get_mastery_percentage(self, user_id: str, category: str) -> float:
        try:
            response = self.client.rpc(
                "get_category_stats",
                {"p_user_id": user_id, "p_threshold": GameConfig.MASTERY_THRESHOLD},
            ).execute()

            data = cast(list[dict[str, Any]], response.data)
            for row in data:
                if row["category"] == category:
                    total = int(row["total"])
                    mastered = int(row["mastered"])
                    return (mastered / total) if total > 0 else 0.0
            return 0.0
        except Exception as e:
            self.telemetry.log_error("get_mastery_percentage failed", e)
            return 0.0

    @measure_time("sb_get_repetition_candidates")
    def get_repetition_candidates(self, user_id: str) -> list[QuestionCandidate]:
        try:
            response = self.client.rpc(
                "get_repetition_candidates",
                {"p_user_id": user_id, "p_threshold": GameConfig.MASTERY_THRESHOLD},
            ).execute()

            data = cast(list[dict[str, Any]], response.data)
            candidates = []
            for row in data:
                q = Question.model_validate(row["json_data"])
                candidates.append(
                    QuestionCandidate(
                        question=q, streak=int(row["streak"]), is_seen=bool(row["seen"])
                    )
                )
            return candidates
        except Exception as e:
            self.telemetry.log_error("get_repetition_candidates failed", e)
            return []

    def get_questions_by_category(
        self, category: str, user_id: str, limit: int = GameConfig.SPRINT_QUESTIONS
    ) -> list[Question]:
        response = (
            self.client.table("questions")
            .select("json_data, user_progress!left(consecutive_correct)")
            .eq("category", category)
            .eq("user_progress.user_id", user_id)
            .execute()
        )

        data = cast(list[dict[str, Any]], response.data)
        candidates: list[tuple[Question, int]] = []

        for row in data:
            question = Question.model_validate(row["json_data"])

            # Extract streak with proper type handling
            user_progress = row.get("user_progress")
            if isinstance(user_progress, dict):
                streak = user_progress.get("consecutive_correct", 0) or 0
            else:
                streak = 0

            candidates.append((question, int(streak)))

        return CategorySelector.prioritize_weak_questions(candidates, limit * 3)

    def get_category_stats(self, user_id: str) -> list[dict[str, int | str]]:
        try:
            response = self.client.rpc(
                "get_category_stats",
                {"p_user_id": user_id, "p_threshold": GameConfig.MASTERY_THRESHOLD},
            ).execute()
            return cast(list[dict[str, int | str]], response.data)
        except Exception as e:
            self.telemetry.log_error("get_category_stats failed", e)
            return []
