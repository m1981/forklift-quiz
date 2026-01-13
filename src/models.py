from enum import Enum
from typing import Dict, Optional, List
from datetime import date
from pydantic import BaseModel, Field


# --- Enums ---
class OptionKey(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# --- Domain Entities ---
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


# --- UI / Application State Models ---

class QuizFeedback(BaseModel):
    type: str  # 'success', 'error', 'info'
    message: str
    explanation: Optional[str] = None


class QuizSessionState(BaseModel):
    """
    SINGLE SOURCE OF TRUTH (SSOT).
    """
    current_q_index: int = 0
    score: int = 0
    last_selected_option: Optional[OptionKey] = None
    last_feedback: Optional[QuizFeedback] = None
    is_complete: bool = False

    # --- NEW FIELDS FOR THE LOOP ---
    # Tracks which questions were missed *in this specific session*
    session_error_ids: List[str] = []
    # Tracks the phase: "Sprint" (Initial) or "Correction" (Forced Review)
    internal_phase: str = "Sprint"


class DashboardConfig(BaseModel):
    title: str
    header_color: str = "#31333F"
    progress_value: float = 0.0
    progress_text: str
    show_streak: bool = True
    show_daily_goal: bool = True
    context_message: Optional[str] = None
    context_color: Optional[str] = None