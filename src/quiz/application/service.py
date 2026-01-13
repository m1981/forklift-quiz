from datetime import date, timedelta
from typing import List

from src.quiz.domain.models import Question, OptionKey, UserProfile, QuizSessionState
from src.quiz.domain.ports import IQuizRepository
from src.quiz.application.strategies import StrategyRegistry, DashboardConfig
# CHANGED IMPORT: Added measure_time
from src.shared.telemetry import Telemetry, measure_time


class QuizService:
    def __init__(self, repo: IQuizRepository):
        self.repo = repo
        self.telemetry = Telemetry("QuizService")

    @property
    def repository(self) -> IQuizRepository:
        return self.repo

    # CHANGED DECORATOR
    @measure_time("initialize_session")
    def get_quiz_questions(self, mode: str, user_id: str) -> List[Question]:
        strategy = StrategyRegistry.get(mode)
        questions = strategy.generate(user_id, self.repo)

        if not questions:
            self.telemetry.log_info("No questions generated", user_id=user_id, mode=mode)

        return questions

    def get_user_profile(self, user_id: str) -> UserProfile:
        return self.repo.get_or_create_profile(user_id)

    def get_dashboard_config(self, mode: str, state: QuizSessionState, user_id: str, total: int) -> DashboardConfig:
        strategy = StrategyRegistry.get(mode)
        profile = self.get_user_profile(user_id)
        return strategy.get_dashboard_config(state, profile, total)

    def is_quiz_complete(self, mode: str, state: QuizSessionState, total: int) -> bool:
        strategy = StrategyRegistry.get(mode)
        return strategy.is_quiz_complete(state, total)

    # CHANGED DECORATOR
    @measure_time("submit_answer")
    def submit_answer(self, user_id: str, question: Question, selected: OptionKey) -> bool:
        today = date.today()
        already_answered = self.repo.was_question_answered_on_date(user_id, question.id, today)

        if already_answered:
            self.telemetry.log_info("Duplicate Answer Attempt", user_id=user_id, q_id=question.id)

        is_correct = (selected == question.correct_option)
        self.repo.save_attempt(user_id, question.id, is_correct)

        self.telemetry.log_info(
            "Answer Submitted",
            user_id=user_id,
            q_id=question.id,
            correct=is_correct,
            duplicate=already_answered
        )
        return is_correct

    # CHANGED DECORATOR
    @measure_time("finalize_session")
    def finalize_session(self, user_id: str):
        profile = self.repo.get_or_create_profile(user_id)
        today = date.today()

        new_streak = profile.streak_days
        if profile.last_login == today - timedelta(days=1):
            new_streak += 1
        elif profile.last_login < today - timedelta(days=1):
            new_streak = 1
        elif profile.last_login == today and new_streak == 0:
            new_streak = 1

        profile.streak_days = new_streak
        profile.daily_progress += 1
        profile.last_login = today

        self.repo.save_profile(profile)
        self.telemetry.log_info("Session Finalized", user_id=user_id, new_streak=new_streak)