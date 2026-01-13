import json
import logging
from datetime import date, timedelta
from typing import List
from src.models import Question, OptionKey, UserProfile, QuizSessionState, DashboardConfig
from src.repository import SQLiteQuizRepository
from src.strategies import StrategyFactory

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(self, repo: SQLiteQuizRepository):
        self.repo = repo

    def initialize_db_from_file(self, json_path: str):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                questions = [Question(**q) for q in data]
                self.repo.seed_questions(questions)
        except Exception as e:
            logger.error(f"Initialization error: {e}")

    def get_user_profile(self, user_id: str) -> UserProfile:
        return self.repo.get_or_create_profile(user_id)

    def get_quiz_questions(self, mode: str, user_id: str) -> List[Question]:
        strategy = StrategyFactory.get_strategy(mode)
        return strategy.generate(user_id, self.repo)

    def get_dashboard_config(self, mode: str, state: QuizSessionState, user_id: str, total_questions: int) -> DashboardConfig:
        strategy = StrategyFactory.get_strategy(mode)
        profile = self.get_user_profile(user_id)
        return strategy.get_dashboard_config(state, profile, total_questions)

    def is_quiz_complete(self, mode: str, state: QuizSessionState, total_questions: int) -> bool:
        strategy = StrategyFactory.get_strategy(mode)
        return strategy.is_quiz_complete(state, total_questions)

    # --- Core Business Logic ---

    def submit_answer(self, user_id: str, question: Question, selected_option: OptionKey) -> bool:
        """
        Records the answer.
        NOTE: Does NOT increment daily progress yet. That happens in finalize_session.
        """
        # 1. Check Duplicate (Idempotency)
        already_answered_today = self.repo.was_question_answered_today(user_id, question.id)

        # 2. Save Attempt
        is_correct = (selected_option == question.correct_option)
        self.repo.save_attempt(user_id, question.id, is_correct)

        if is_correct:
            logger.info(f"✅ SERVICE: Answer Correct for Q{question.id}.")
        else:
            logger.info(f"❌ SERVICE: Answer Incorrect for Q{question.id}.")

        return is_correct

    def finalize_session(self, user_id: str):
        """
        Called when the user successfully completes the loop (Sprint + Corrections).
        This is the 'Reward' phase.
        """
        logger.info(f"🏆 SERVICE: Finalizing session for {user_id}. Incrementing stats.")
        self._update_user_stats(user_id)

    def _update_user_stats(self, user_id: str):
        """
        Pure Business Logic: Calculates streaks and progress.
        """
        profile = self.repo.get_or_create_profile(user_id)
        today = date.today()

        # Calculate Streak
        new_streak = profile.streak_days
        if profile.last_login == today - timedelta(days=1):
            new_streak += 1
        elif profile.last_login < today - timedelta(days=1):
            new_streak = 1
        elif profile.last_login == today:
            if new_streak == 0: new_streak = 1

        # Update Progress
        new_progress = profile.daily_progress + 1

        # Update Profile Object
        profile.streak_days = new_streak
        profile.daily_progress = new_progress
        profile.last_login = today

        # Persist
        self.repo.save_profile(profile)