from abc import ABC, abstractmethod
from typing import List
import random
import logging
from src.models import Question
from src.repository import SQLiteQuizRepository

logger = logging.getLogger(__name__)


class QuestionStrategy(ABC):
    """
    Interface for question generation algorithms.
    """

    @abstractmethod
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        pass


class StandardStrategy(QuestionStrategy):
    """
    Returns all available questions in the database.
    """

    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        return repo.get_all_questions()


class ReviewStrategy(QuestionStrategy):
    """
    Returns only questions the user has currently marked as incorrect.
    """

    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        all_questions = repo.get_all_questions()
        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))

        # Filter
        filtered = [q for q in all_questions if q.id in incorrect_ids]
        logger.info(f"Review Strategy: Found {len(filtered)} incorrect questions for {user_id}")
        return filtered


class DailySprintStrategy(QuestionStrategy):
    """
    Complex Logic:
    1. Calculate remaining daily goal.
    2. Mix Struggling (30%) + New (70%).
    3. Backfill with Mastered if needed.
    """

    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        all_questions = repo.get_all_questions()
        profile = repo.get_or_create_profile(user_id)

        # 1. Determine Batch Size
        needed = profile.daily_goal - profile.daily_progress
        if needed <= 0:
            needed = 5  # Bonus round

        logger.info(f"Sprint Strategy: User needs {needed} questions.")

        # 2. Fetch Sets
        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))
        attempted_ids = set(repo.get_all_attempted_ids(user_id))

        sprint_questions = []

        # 3. Add Struggling (Max 30% of batch)
        struggling_count = min(len(incorrect_ids), int(needed * 0.3) + 1)
        struggling_candidates = [q for q in all_questions if q.id in incorrect_ids]
        random.shuffle(struggling_candidates)
        sprint_questions.extend(struggling_candidates[:struggling_count])

        # 4. Fill with New Questions
        remaining_slots = needed - len(sprint_questions)
        new_candidates = [q for q in all_questions if q.id not in attempted_ids]
        random.shuffle(new_candidates)
        sprint_questions.extend(new_candidates[:remaining_slots])

        # 5. Backfill with Mastered (if we ran out of new questions)
        if len(sprint_questions) < needed:
            remaining_slots = needed - len(sprint_questions)
            # Mastered = Attempted AND NOT Incorrect
            mastered_candidates = [q for q in all_questions if q.id in attempted_ids and q.id not in incorrect_ids]
            random.shuffle(mastered_candidates)
            sprint_questions.extend(mastered_candidates[:remaining_slots])

        return sprint_questions


class StrategyFactory:
    """
    Maps string keys (from UI) to Strategy instances.
    """
    _strategies = {
        "Standard": StandardStrategy(),
        "Review (Struggling Only)": ReviewStrategy(),
        "Daily Sprint": DailySprintStrategy()
    }

    @classmethod
    def get_strategy(cls, mode_name: str) -> QuestionStrategy:
        return cls._strategies.get(mode_name, StandardStrategy())