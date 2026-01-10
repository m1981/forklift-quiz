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
        is_correct = (selected_option == question.correct_option)
        self.repo.save_attempt(user_id, question.id, is_correct)
        self.repo.update_profile_stats(user_id, increment_progress=True)
        return is_correct