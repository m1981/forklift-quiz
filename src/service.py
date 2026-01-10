import json
import logging
from typing import List
from src.models import Question, OptionKey
from src.repository import SQLiteQuizRepository

logger = logging.getLogger(__name__)


class QuizService:
    def __init__(self, repo: SQLiteQuizRepository):
        self.repo = repo

    def initialize_db_from_file(self, json_path: str):
        """Sequence 1: Loading JSON"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Validate data against Pydantic model before sending to DB
                questions = [Question(**q) for q in data]
                self.repo.seed_questions(questions)
        except FileNotFoundError:
            logger.warning(f"Seed file not found at {json_path}. Skipping seed.")
        except json.JSONDecodeError:
            logger.error(f"Seed file at {json_path} is invalid JSON.")
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")

    def get_quiz_questions(self, mode: str, user_id: str) -> List[Question]:
        """Sequence 2 & 3: Logic Routing"""
        all_questions = self.repo.get_all_questions()

        if not all_questions:
            logger.warning("No questions returned from repository.")
            return []

        if mode == "Review (Struggling Only)":
            incorrect_ids = self.repo.get_incorrect_question_ids(user_id)
            # Filter logic
            filtered = [q for q in all_questions if q.id in incorrect_ids]
            logger.info(f"User {user_id} requested review. Found {len(filtered)} struggling questions.")
            return filtered

        return all_questions

    def submit_answer(self, user_id: str, question: Question, selected_option: OptionKey) -> bool:
        """Sequence 2: Validation & Save"""
        is_correct = (selected_option == question.correct_option)

        # We save the result regardless of whether it's right or wrong
        # This ensures the 'Review' mode gets updated data
        self.repo.save_attempt(user_id, question.id, is_correct)

        return is_correct