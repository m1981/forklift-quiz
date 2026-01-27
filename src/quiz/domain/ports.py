from abc import ABC, abstractmethod

from src.quiz.domain.models import Question, QuestionCandidate, UserProfile


class IQuizRepository(ABC):
    # --- REMOVED: get_all_questions (Unused in app flow) ---

    @abstractmethod
    def get_questions_by_ids(self, question_ids: list[str]) -> list[Question]:
        pass

    @abstractmethod
    def seed_questions(self, questions: list[Question]) -> None:
        pass

    @abstractmethod
    def get_or_create_profile(self, user_id: str) -> UserProfile:
        pass

    @abstractmethod
    def save_profile(self, profile: UserProfile) -> None:
        pass

    @abstractmethod
    def save_attempt(self, user_id: str, question_id: str, is_correct: bool) -> None:
        pass

    # --- REMOVED: was_question_answered_on_date (Unused) ---
    # --- REMOVED: get_incorrect_question_ids (Unused) ---

    @abstractmethod
    def get_mastery_percentage(self, user_id: str, category: str) -> float:
        pass

    # --- REMOVED: get_all_attempted_ids (Unused) ---
    # --- REMOVED: reset_user_progress (Unused) ---

    # --- NEW METHODS FOR MASTERY & CATEGORIES ---

    # --- REMOVED: get_smart_mix (Replaced by get_repetition_candidates) ---

    @abstractmethod
    def get_repetition_candidates(self, user_id: str) -> list[QuestionCandidate]:
        """
        Fetches raw candidates for the Spaced Repetition algorithm.
        """
        pass

    @abstractmethod
    def get_questions_by_category(
        self, category: str, user_id: str, limit: int = 15
    ) -> list[Question]:
        pass
