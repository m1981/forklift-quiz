from abc import ABC, abstractmethod

from src.quiz.domain.models import Question, QuestionCandidate, UserProfile


class IQuizRepository(ABC):
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

    @abstractmethod
    def get_mastery_percentage(self, user_id: str, category: str) -> float:
        pass

    @abstractmethod
    def get_repetition_candidates(self, user_id: str) -> list[QuestionCandidate]:
        """
        Fetches raw candidates for the Spaced Repetition algorithm.
        """
        pass

    @abstractmethod
    def get_questions_by_category(
        self, category: str, user_id: str, limit: int
    ) -> list[Question]:
        pass

    # --- FIX: Added missing abstract method ---
    @abstractmethod
    def get_category_stats(self, user_id: str) -> list[dict[str, int | str]]:
        """
        Returns statistics per category for the dashboard.
        """
        pass
