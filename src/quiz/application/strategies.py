import random
from abc import ABC, abstractmethod
from typing import List, Dict

from pydantic import BaseModel

from src.quiz.domain.models import Question, QuizSessionState, UserProfile
from src.quiz.domain.ports import IQuizRepository
# CHANGED IMPORT: Added measure_time
from src.shared.telemetry import Telemetry, measure_time


# --- DTO for UI Configuration ---
class DashboardConfig(BaseModel):
    title: str
    header_color: str = "#31333F"
    progress_value: float = 0.0
    progress_text: str
    show_streak: bool = True
    show_daily_goal: bool = True
    context_message: str | None = None
    context_color: str | None = None


# --- Interface ---
class IQuestionStrategy(ABC):
    @abstractmethod
    def generate(self, user_id: str, repo: IQuizRepository) -> List[Question]:
        pass

    @abstractmethod
    def is_quiz_complete(self, state: QuizSessionState, total_questions: int) -> bool:
        pass

    @abstractmethod
    def get_dashboard_config(self, state: QuizSessionState, profile: UserProfile, total: int) -> DashboardConfig:
        pass


# --- Concrete Strategies ---

class DailySprintStrategy(IQuestionStrategy):
    def __init__(self):
        self.telemetry = Telemetry("Strategy.Sprint")

    # CHANGED DECORATOR
    @measure_time("generate_sprint")
    def generate(self, user_id: str, repo: IQuizRepository) -> List[Question]:
        all_questions = repo.get_all_questions()
        profile = repo.get_or_create_profile(user_id)

        sprint_size = 5 if profile.is_bonus_mode() else 10

        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))
        attempted_ids = set(repo.get_all_attempted_ids(user_id))

        selection = []

        # 1. Struggling (30%)
        struggling = [q for q in all_questions if q.id in incorrect_ids]
        random.shuffle(struggling)
        selection.extend(struggling[:int(sprint_size * 0.3) + 1])

        # 2. New Questions
        new_qs = [q for q in all_questions if q.id not in attempted_ids]
        random.shuffle(new_qs)
        needed = sprint_size - len(selection)
        selection.extend(new_qs[:needed])

        # 3. Fill with Mastered
        if len(selection) < sprint_size:
            mastered = [q for q in all_questions if q.id in attempted_ids and q.id not in incorrect_ids]
            random.shuffle(mastered)
            selection.extend(mastered[:sprint_size - len(selection)])

        self.telemetry.log_info("Generated Questions", count=len(selection), mode="Sprint")
        return selection

    def is_quiz_complete(self, state: QuizSessionState, total_questions: int) -> bool:
        return state.current_q_index >= total_questions - 1

    def get_dashboard_config(self, state: QuizSessionState, profile: UserProfile, total: int) -> DashboardConfig:
        if state.internal_phase == "Correction":
            return DashboardConfig(
                title="🚨 Poprawa Błędów",
                header_color="#ff9800",
                progress_value=state.current_q_index / total if total else 1.0,
                progress_text=f"Poprawa: {state.current_q_index + 1}/{total}",
                show_streak=False,
                context_message="Musisz poprawić błędy, aby zaliczyć dzień."
            )

        if profile.is_bonus_mode():
            return DashboardConfig(
                title="🔥 Runda Bonusowa",
                header_color="#673AB7",
                progress_value=1.0,
                progress_text=f"Nadgodziny: {profile.daily_progress}/{profile.daily_goal} 🔥"
            )

        goal_progress = min(profile.daily_progress / profile.daily_goal, 1.0) if profile.daily_goal > 0 else 1.0
        return DashboardConfig(
            title="🚀 Codzienny Sprint",
            progress_value=goal_progress,
            progress_text=f"Cel Dzienny: {profile.daily_progress}/{profile.daily_goal}"
        )


class ReviewStrategy(IQuestionStrategy):
    def __init__(self):
        self.telemetry = Telemetry("Strategy.Review")

    # CHANGED DECORATOR
    @measure_time("generate_review")
    def generate(self, user_id: str, repo: IQuizRepository) -> List[Question]:
        incorrect_ids = repo.get_incorrect_question_ids(user_id)
        return repo.get_questions_by_ids(incorrect_ids)

    def is_quiz_complete(self, state: QuizSessionState, total_questions: int) -> bool:
        return state.current_q_index >= total_questions - 1

    def get_dashboard_config(self, state: QuizSessionState, profile: UserProfile, total: int) -> DashboardConfig:
        return DashboardConfig(
            title="🛠️ Tryb Poprawy",
            header_color="#ff4b4b",
            progress_value=state.current_q_index / total if total else 1.0,
            progress_text=f"Naprawiono: {state.current_q_index}/{total}",
            show_streak=False,
            context_message=f"Pozostało: {total - state.current_q_index}"
        )


# --- Registry (OCP) ---
class StrategyRegistry:
    _strategies: Dict[str, IQuestionStrategy] = {}

    @classmethod
    def register(cls, name: str, strategy: IQuestionStrategy):
        cls._strategies[name] = strategy

    @classmethod
    def get(cls, name: str) -> IQuestionStrategy:
        return cls._strategies.get(name, cls._strategies.get("Daily Sprint"))


StrategyRegistry.register("Daily Sprint", DailySprintStrategy())
StrategyRegistry.register("Review (Struggling Only)", ReviewStrategy())