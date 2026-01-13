from enum import Enum
from typing import Dict, Optional
from datetime import date
from pydantic import BaseModel, Field

class OptionKey(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

class Question(BaseModel):
    id: str = Field(..., description="Unique identifier")
    text: str = Field(..., description="The question text")
    image_path: Optional[str] = Field(None, description="Path to image file relative to root")
    options: Dict[OptionKey, str]
    correct_option: OptionKey
    explanation: Optional[str] = Field(None, description="Explanation for the correct answer")
    hint: Optional[str] = Field(None, description="A helpful clue for the user")
    category: str = Field("Ogólne", description="The topic/domain of the question")

class QuizSessionState(BaseModel):
    """Tracks the transient state of the UI"""
    current_q_index: int = 0
    score: int = 0
    last_answer_correct: Optional[bool] = None
    quiz_complete: bool = False

class UserProfile(BaseModel):
    user_id: str
    streak_days: int = 0
    last_login: date = Field(default_factory=date.today)
    daily_goal: int = 3
    daily_progress: int = 0
    last_daily_reset: date = Field(default_factory=date.today)