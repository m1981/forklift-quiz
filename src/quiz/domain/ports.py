from abc import ABC, abstractmethod
from datetime import date

from src.quiz.domain.models import Question, UserProfile


class IQuizRepository(ABC):
    @abstractmethod
    def get_all_questions(self) -> list[Question]:
        pass

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
    def was_question_answered_on_date(
        self, user_id: str, question_id: str, check_date: date
    ) -> bool:
        """
        Checks if a question was answered on a specific date.
        Passing the date explicitly makes this testable (no hidden 'now()' calls).
        """
        pass

    @abstractmethod
    def get_incorrect_question_ids(self, user_id: str) -> list[str]:
        pass

    @abstractmethod
    def get_all_attempted_ids(self, user_id: str) -> list[str]:
        pass

    @abstractmethod
    def reset_user_progress(self, user_id: str) -> None:
        pass
