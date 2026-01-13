from enum import Enum
from typing import Dict, Optional, List
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

class UserProfile(BaseModel):
    user_id: str
    streak_days: int = 0
    last_login: date = Field(default_factory=date.today)
    daily_goal: int = 3
    daily_progress: int = 0
    last_daily_reset: date = Field(default_factory=date.today)

# --- UI / Application State Models (The "Typed Container") ---

class QuizFeedback(BaseModel):
    """Represents the result of a user's action to be displayed."""
    type: str  # 'success', 'error', 'info'
    message: str
    explanation: Optional[str] = None

class QuizSessionState(BaseModel):
    """
    SINGLE SOURCE OF TRUTH (SSOT).
    This object holds the entire transient state of the active quiz session.
    """
    current_q_index: int = 0
    score: int = 0
    # We store the ID of the last selected option to highlight it in the UI
    last_selected_option: Optional[OptionKey] = None
    # Structured feedback object
    last_feedback: Optional[QuizFeedback] = None
    # Is the quiz officially finished?
    is_complete: bool = False

# --- DTOs (Data Transfer Objects) for Strategy Pattern ---

class DashboardConfig(BaseModel):
    """
    Decouples the UI from the Logic.
    The Strategy creates this, the View renders it.
    """
    title: str
    header_color: str = "#31333F" # Default dark grey
    progress_value: float = 0.0   # 0.0 to 1.0
    progress_text: str
    show_streak: bool = True
    show_daily_goal: bool = True
    # Optional: Custom message for the specific mode (e.g., "3 errors remaining")
    context_message: Optional[str] = None
    context_color: Optional[str] = None