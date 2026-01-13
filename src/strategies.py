from abc import ABC, abstractmethod
from typing import List
import random
import logging
from src.models import Question, QuizSessionState, UserProfile, DashboardConfig
from src.repository import SQLiteQuizRepository

logger = logging.getLogger(__name__)


class QuestionStrategy(ABC):
    @abstractmethod
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        pass

    @abstractmethod
    def is_quiz_complete(self, state: QuizSessionState, total_questions: int) -> bool:
        pass

    @abstractmethod
    def get_dashboard_config(self, state: QuizSessionState, profile: UserProfile,
                             total_questions: int) -> DashboardConfig:
        pass


class ReviewStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        logger.info(f"🧠 STRATEGY: Starting Review generation for {user_id}")
        all_questions = repo.get_all_questions()
        incorrect_ids_list = repo.get_incorrect_question_ids(user_id)
        incorrect_ids_set = set(incorrect_ids_list)
        filtered = [q for q in all_questions if q.id in incorrect_ids_set]
        return filtered

    def is_quiz_complete(self, state: QuizSessionState, total_questions: int) -> bool:
        return state.current_q_index >= total_questions - 1

    def get_dashboard_config(self, state: QuizSessionState, profile: UserProfile,
                             total_questions: int) -> DashboardConfig:
        remaining = total_questions - state.current_q_index
        return DashboardConfig(
            title="🛠️ Tryb Poprawy Błędów",
            header_color="#ff4b4b",
            progress_value=state.current_q_index / total_questions if total_questions > 0 else 1.0,
            progress_text=f"Naprawiono: {state.current_q_index}/{total_questions}",
            show_streak=False,
            show_daily_goal=False,
            context_message=f"Pozostało do naprawienia: {remaining}",
            context_color="#fff0f0"
        )


class DailySprintStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        logger.info(f"🧠 STRATEGY: Starting Sprint generation for {user_id}")
        all_questions = repo.get_all_questions()
        profile = repo.get_or_create_profile(user_id)

        # --- LOGIC FIX: Standardize Sprint Size ---
        # Old logic: needed = goal - progress (Mixed units)
        # New logic: Fixed size based on status

        if profile.daily_progress >= profile.daily_goal:
            sprint_size = 5  # Bonus Round
            logger.info("🧠 STRATEGY: Daily Goal met. Generating BONUS round (5 questions).")
        else:
            sprint_size = 10  # Standard Sprint
            logger.info("🧠 STRATEGY: Daily Goal active. Generating STANDARD round (10 questions).")

        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))
        attempted_ids = set(repo.get_all_attempted_ids(user_id))
        sprint_questions = []

        # 1. Priority: Struggling (30%)
        struggling_count = min(len(incorrect_ids), int(sprint_size * 0.3) + 1)
        struggling_candidates = [q for q in all_questions if q.id in incorrect_ids]
        random.shuffle(struggling_candidates)
        sprint_questions.extend(struggling_candidates[:struggling_count])

        # 2. Priority: New
        remaining_slots = sprint_size - len(sprint_questions)
        new_candidates = [q for q in all_questions if q.id not in attempted_ids]
        random.shuffle(new_candidates)
        sprint_questions.extend(new_candidates[:remaining_slots])

        # 3. Priority: Mastered
        if len(sprint_questions) < sprint_size:
            remaining_slots = sprint_size - len(sprint_questions)
            mastered_candidates = [q for q in all_questions if q.id in attempted_ids and q.id not in incorrect_ids]
            random.shuffle(mastered_candidates)
            sprint_questions.extend(mastered_candidates[:remaining_slots])

        return sprint_questions

    def is_quiz_complete(self, state: QuizSessionState, total_questions: int) -> bool:
        return state.current_q_index >= total_questions - 1

    def get_dashboard_config(self, state: QuizSessionState, profile: UserProfile,
                             total_questions: int) -> DashboardConfig:
        # DYNAMIC CONFIG BASED ON PHASE
        if state.internal_phase == "Correction":
            return DashboardConfig(
                title="🚨 Poprawa Błędów (Wymagana)",
                header_color="#ff9800",  # Orange
                progress_value=state.current_q_index / total_questions if total_questions > 0 else 1.0,
                progress_text=f"Poprawa: {state.current_q_index + 1}/{total_questions}",
                show_streak=False,
                show_daily_goal=False,
                context_message="Musisz poprawić błędy, aby zaliczyć dzień.",
                context_color="#fff3e0"
            )

        # --- UI FIX: Handle Bonus Round Display ---
        is_bonus = profile.daily_progress >= profile.daily_goal

        if is_bonus:
            # Bonus Mode UI
            return DashboardConfig(
                title="🔥 Runda Bonusowa",
                header_color="#673AB7",  # Purple for Bonus
                progress_value=1.0,
                progress_text=f"Nadgodziny: {profile.daily_progress}/{profile.daily_goal} 🔥",
                show_streak=True,
                show_daily_goal=True
            )
        else:
            # Standard Sprint UI
            goal_progress = min(profile.daily_progress / profile.daily_goal, 1.0) if profile.daily_goal > 0 else 1.0
            return DashboardConfig(
                title="🚀 Codzienny Sprint",
                header_color="#31333F",
                progress_value=goal_progress,
                progress_text=f"Cel Dzienny: {profile.daily_progress}/{profile.daily_goal}",
                show_streak=True,
                show_daily_goal=True
            )


class StrategyFactory:
    _strategies = {
        "Daily Sprint": DailySprintStrategy(),
        "Review (Struggling Only)": ReviewStrategy()
    }

    @classmethod
    def get_strategy(cls, mode_name: str) -> QuestionStrategy:
        if "Sprint" in mode_name:
            return cls._strategies["Daily Sprint"]
        if "Powtórka" in mode_name or "Review" in mode_name:
            return cls._strategies["Review (Struggling Only)"]
        return cls._strategies["Daily Sprint"]