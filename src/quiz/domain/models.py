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
