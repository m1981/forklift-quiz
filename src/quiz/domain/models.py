from dataclasses import dataclass
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from src.config import GameConfig


# --- Enums ---
class OptionKey(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# --- Entities ---
class Question(BaseModel):
    id: str
    text: str
    image_path: str | None = None
    options: dict[OptionKey, str]
    correct_option: OptionKey
    explanation: str | None = None
    hint: str | None = None
    category: str = "Ogólne"


# --- (Data Transfer Object) ---
@dataclass
class QuestionCandidate:
    """
    Represents a question eligible for selection,
    decoupled from the database implementation.
    """

    question: Question
    streak: int
    is_seen: bool


class UserProfile(BaseModel):
    user_id: str
    streak_days: int = 0
    last_login: date = Field(default_factory=date.today)
    daily_progress: int = 0
    last_daily_reset: date = Field(default_factory=date.today)

    daily_goal: int = GameConfig.DAILY_GOAL
    has_completed_onboarding: bool = False

    def is_bonus_mode(self) -> bool:
        return self.daily_progress >= self.daily_goal


class QuizSessionState(BaseModel):
    """
    Encapsulates the state of a running quiz.
    """

    current_q_index: int = 0
    score: int = 0
    session_error_ids: list[str] = []
    internal_phase: str = "Sprint"  # 'Sprint' or 'Correction'
    is_complete: bool = False

    def record_correct_answer(self) -> None:
        self.score += 1

    def record_error(self, question_id: str) -> None:
        if question_id not in self.session_error_ids:
            self.session_error_ids.append(question_id)

    def resolve_error(self, question_id: str) -> None:
        if question_id in self.session_error_ids:
            self.session_error_ids.remove(question_id)

    def next_question(self) -> None:
        self.current_q_index += 1

    def reset(self, phase: str = "Sprint") -> None:
        self.current_q_index = 0
        self.score = 0
        self.session_error_ids = []
        self.internal_phase = phase
        self.is_complete = False
