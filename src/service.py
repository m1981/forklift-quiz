import json
import logging
from typing import List
from src.models import Question, OptionKey, UserProfile
from src.repository import SQLiteQuizRepository
from src.strategies import StrategyFactory # <--- NEW IMPORT

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
        """
        Delegates logic to the appropriate Strategy.
        """
        strategy = StrategyFactory.get_strategy(mode)
        return strategy.generate(user_id, self.repo)

    def submit_answer(self, user_id: str, question: Question, selected_option: OptionKey) -> bool:
        # 1. CRITICAL: Check history BEFORE saving the new attempt.
        # If we save first, the DB timestamp updates to 'now', and this check becomes uselessly True.
        already_answered_today = self.repo.was_question_answered_today(user_id, question.id)

        if already_answered_today:
            logger.info(f"🚫 SERVICE: Q{question.id} was already answered today. Daily Goal will NOT increment.")
        else:
            logger.info(f"✅ SERVICE: First time answering Q{question.id} today. Counting towards Goal.")

        # 2. Save the attempt (This updates the DB timestamp to NOW)
        is_correct = (selected_option == question.correct_option)
        self.repo.save_attempt(user_id, question.id, is_correct)

        # 3. Update Stats
        # We only increment if it was NOT already answered today
        should_increment = not already_answered_today
        self.repo.update_profile_stats(user_id, increment_progress=should_increment)

        return is_correct