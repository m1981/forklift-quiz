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


class ReviewStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        logger.info(f"🧠 STRATEGY: Starting Review generation for {user_id}")

        # 1. Get All Questions
        all_questions = repo.get_all_questions()

        # 2. Get Incorrect IDs
        incorrect_ids_list = repo.get_incorrect_question_ids(user_id)
        incorrect_ids_set = set(incorrect_ids_list)

        # --- DEEP DEBUG LOGGING ---
        logger.debug(f"🧠 DEBUG: DB returned {len(incorrect_ids_list)} incorrect IDs: {incorrect_ids_list}")

        # Check for matches manually to log failures
        match_count = 0
        for q in all_questions:
            if q.id in incorrect_ids_set:
                match_count += 1
            # Log the first failure to see mismatch
            elif q.id == '108' or q.id == 108:  # Hardcoded check for your specific case
                logger.warning(f"⚠️ MISMATCH FOUND: Question 108 exists in DB but 'in' check failed!")
                logger.warning(f"   -> Question ID in Memory: '{q.id}' ({type(q.id)})")
                logger.warning(f"   -> Incorrect Set contains: {incorrect_ids_set}")
        # --------------------------

        filtered = [q for q in all_questions if q.id in incorrect_ids_set]

        logger.info(f"🧠 STRATEGY: Final Review Set: {len(filtered)} questions (Expected: {len(incorrect_ids_set)})")
        return filtered


class DailySprintStrategy(QuestionStrategy):
    def generate(self, user_id: str, repo: SQLiteQuizRepository) -> List[Question]:
        logger.info(f"🧠 STRATEGY: Starting Sprint generation for {user_id}")
        all_questions = repo.get_all_questions()
        profile = repo.get_or_create_profile(user_id)

        needed = profile.daily_goal - profile.daily_progress
        logger.debug(f"🧠 STRATEGY: Goal={profile.daily_goal}, Progress={profile.daily_progress}, Needed={needed}")

        if needed <= 0:
            needed = 5
            logger.info("🧠 STRATEGY: Goal met. Triggering Bonus Round (5 questions).")

        incorrect_ids = set(repo.get_incorrect_question_ids(user_id))
        attempted_ids = set(repo.get_all_attempted_ids(user_id))

        logger.debug(f"🧠 STRATEGY: Pool Stats -> Incorrect: {len(incorrect_ids)}, Attempted: {len(attempted_ids)}")

        sprint_questions = []

        # 1. Priority: Struggling Questions (30%)
        struggling_count = min(len(incorrect_ids), int(needed * 0.3) + 1)
        struggling_candidates = [q for q in all_questions if q.id in incorrect_ids]
        random.shuffle(struggling_candidates)
        sprint_questions.extend(struggling_candidates[:struggling_count])

        # 2. Priority: New Questions
        remaining_slots = needed - len(sprint_questions)
        new_candidates = [q for q in all_questions if q.id not in attempted_ids]
        random.shuffle(new_candidates)
        sprint_questions.extend(new_candidates[:remaining_slots])

        # 3. Priority: Mastered (Backfill if we ran out of new questions)
        if len(sprint_questions) < needed:
            remaining_slots = needed - len(sprint_questions)
            mastered_candidates = [q for q in all_questions if q.id in attempted_ids and q.id not in incorrect_ids]
            random.shuffle(mastered_candidates)
            sprint_questions.extend(mastered_candidates[:remaining_slots])

        logger.info(f"🧠 STRATEGY: Final Sprint Set generated with {len(sprint_questions)} questions.")
        return sprint_questions


class StrategyFactory:
    _strategies = {
        "Daily Sprint": DailySprintStrategy(),
        "Review (Struggling Only)": ReviewStrategy()
    }

    @classmethod
    def get_strategy(cls, mode_name: str) -> QuestionStrategy:
        return cls._strategies.get(mode_name, DailySprintStrategy())