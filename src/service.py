from typing import List
from src.models import Question, OptionKey
from src.repository import SQLiteQuizRepository


class QuizService:
    def __init__(self, repo: SQLiteQuizRepository):
        self.repo = repo

    def initialize_db_from_file(self, json_path: str):
        """Loads the initial JSON into SQLite."""
        import json
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                questions = [Question(**q) for q in data]
                self.repo.seed_questions(questions)
        except FileNotFoundError:
            pass  # Handle gracefully if file missing

    def get_quiz_questions(self, mode: str, user_id: str) -> List[Question]:
        """
        Returns questions based on mode:
        - 'Standard': All questions
        - 'Review': Only questions the user previously got wrong
        """
        all_questions = self.repo.get_all_questions()

        if mode == "Review (Struggling Only)":
            incorrect_ids = self.repo.get_incorrect_question_ids(user_id)
            # Filter all questions to find only the incorrect ones
            return [q for q in all_questions if q.id in incorrect_ids]

        return all_questions

    def submit_answer(self, user_id: str, question: Question, selected_option: OptionKey) -> bool:
        is_correct = (selected_option == question.correct_option)
        self.repo.save_attempt(user_id, question.id, is_correct)
        return is_correct