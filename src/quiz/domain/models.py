from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.config import GameConfig


# --- Enums ---
class OptionKey(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class Language(str, Enum):
    PL = "pl"  # Polish (Default/Exam Language)
    EN = "en"  # English
    UK = "uk"  # Ukrainian
    KA = "ka"  # Georgian


# --- Value Objects ---
class LocalizedContent(BaseModel):
    """Holds the translatable parts of a question."""

    explanation: str | None = None
    hint: str | None = None


# --- Entities ---
class Question(BaseModel):
    id: str
    text: str  # ALWAYS Polish
    image_path: str | None = None
    options: dict[OptionKey, str]  # ALWAYS Polish
    correct_option: OptionKey

    # Default (Polish) content
    explanation: str | None = None
    hint: str | None = None
    category: str = "Ogólne"

    # Translations map: Language Code -> Content
    translations: dict[Language, LocalizedContent] = Field(default_factory=dict)

    def get_explanation(self, lang: Language) -> str | None:
        """
        Returns explanation in requested language.
        Falls back to Polish if translation is missing.
        """
        if lang == Language.PL:
            return self.explanation

        # Try to find translation
        if lang in self.translations:
            content = self.translations[lang]
            if content.explanation:
                return content.explanation

        # Fallback to Polish (Source of Truth)
        return self.explanation

    def get_hint(self, lang: Language) -> str | None:
        """
        Returns hint in requested language.
        Falls back to Polish if translation is missing.
        """
        if lang == Language.PL:
            return self.hint

        if lang in self.translations:
            content = self.translations[lang]
            if content.hint:
                return content.hint

        return self.hint


# --- (Data Transfer Object) ---
@dataclass
class QuestionCandidate:
    question: Question
    streak: int
    is_seen: bool


class UserProfile(BaseModel):
    user_id: str
    streak_days: int = 0
    last_login: date = Field(default_factory=date.today)
    daily_progress: int = 0
    last_daily_reset: date = Field(default_factory=date.today)
    preferred_language: Language = Language.PL
    daily_goal: int = GameConfig.DAILY_GOAL
    has_completed_onboarding: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_bonus_mode(self) -> bool:
        return self.daily_progress >= self.daily_goal
