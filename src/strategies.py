from abc import ABC, abstractmethod
from typing import List
import random
import logging
from src.models import Question
from src.repository import SQLiteQuizRepository

logger = logging.getLogger(__name__)


class QuestionStrategy(ABC):
    @abstractmethod
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        pass


class StandardStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        return repo.get_all_questions()


class ReviewStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        logger.info(f"🧠 STRATEGY: Starting Review generation for {user_id}")

        all_questions = repo.get_all_questions()
        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))

        logger.debug(f"🧠 STRATEGY: Total Questions in DB: {len(all_questions)}")
        logger.debug(f"🧠 STRATEGY: Incorrect IDs found: {incorrect_ids}")

        # Filter
        filtered = [q for q in all_questions if q.id in incorrect_ids]

        logger.info(f"🧠 STRATEGY: Final Review Set: {len(filtered)} questions.")
        return filtered


class DailySprintStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        logger.info(f"🧠 STRATEGY: Starting Sprint generation for {user_id}")

        all_questions = repo.get_all_questions()
        profile = repo.get_or_create_profile(user_id)

        # 1. Determine Batch Size
        needed = profile.daily_goal - profile.daily_progress
        logger.debug(f"🧠 STRATEGY: Goal={profile.daily_goal}, Progress={profile.daily_progress}, Needed={needed}")

        if needed <= 0:
            needed = 5
            logger.info("🧠 STRATEGY: Goal met. Triggering Bonus Round (5 questions).")

        logger.info(f"Sprint Strategy: User needs {needed} questions.")

        # 2. Fetch Sets
        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))
        attempted_ids = set(repo.get_all_attempted_ids(user_id))

        logger.debug(f"🧠 STRATEGY: Pool Stats -> Incorrect: {len(incorrect_ids)}, Attempted: {len(attempted_ids)}")

        sprint_questions = []

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

        logger.info(f"🧠 STRATEGY: Final Sprint Set generated with {len(sprint_questions)} questions.")
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