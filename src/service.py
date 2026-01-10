import json
import logging
import random
from typing import List
from src.models import Question, OptionKey, UserProfile
from src.repository import SQLiteQuizRepository

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
        all_questions = self.repo.get_all_questions()
        if not all_questions:
            return []

        # 1. Review Mode
        if mode == "Review (Struggling Only)":
            incorrect_ids = self.repo.get_incorrect_question_ids(user_id)
            return [q for q in all_questions if q.id in incorrect_ids]

        # 2. Daily Sprint Mode (The Gamification Logic)
        if mode == "Daily Sprint":
            profile = self.repo.get_or_create_profile(user_id)

            # Calculate how many needed to finish the day
            needed = profile.daily_goal - profile.daily_progress
            if needed <= 0:
                # Goal done? Give a "Bonus Round" of 5 random questions
                needed = 5

                # Fetch IDs
            incorrect_ids = set(self.repo.get_incorrect_question_ids(user_id))
            attempted_ids = set(self.repo.get_all_attempted_ids(user_id))

            # Logic: Mix Struggling (30%) + New (70%)
            sprint_questions = []

            # A. Add Struggling (Max 3 or 30% of needed)
            struggling_count = min(len(incorrect_ids), int(needed * 0.3) + 1)
            struggling_candidates = [q for q in all_questions if q.id in incorrect_ids]
            # Shuffle to not always show same struggling ones first
            random.shuffle(struggling_candidates)
            sprint_questions.extend(struggling_candidates[:struggling_count])

            # B. Fill rest with New Questions
            remaining_slots = needed - len(sprint_questions)
            new_candidates = [q for q in all_questions if q.id not in attempted_ids]
            random.shuffle(new_candidates)
            sprint_questions.extend(new_candidates[:remaining_slots])

            # C. If still need more (e.g., no new questions left), fill with Mastered (Review)
            if len(sprint_questions) < needed:
                remaining_slots = needed - len(sprint_questions)
                mastered_candidates = [q for q in all_questions if q.id in attempted_ids and q.id not in incorrect_ids]
                random.shuffle(mastered_candidates)
                sprint_questions.extend(mastered_candidates[:remaining_slots])

            return sprint_questions

        # 3. Standard Mode (Default)
        return all_questions

    def submit_answer(self, user_id: str, question: Question, selected_option: OptionKey) -> bool:
        is_correct = (selected_option == question.correct_option)

        # 1. Save the attempt result
        self.repo.save_attempt(user_id, question.id, is_correct)

        # 2. Update Gamification Stats (Streak, Daily Progress)
        self.repo.update_profile_stats(user_id, increment_progress=True)

        return is_correct