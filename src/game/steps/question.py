# src/game/steps/question.py

import logging
from dataclasses import dataclass
from typing import Any, Union

from src.config import GameConfig
from src.game.core import GameContext, GameStep, UIModel
from src.quiz.domain.models import Language, Question  # <--- Import Language

logger = logging.getLogger(__name__)


@dataclass
class QuestionStepPayload:
    question: Question
    current_index: int
    total_count: int
    flow_title: str
    category_name: str
    category_mastery: float
    # --- NEW FIELDS FOR UX ---
    session_history: list[bool | None]
    current_streak: int
    # -------------------------
    # --- LOCALIZATION ---
    preferred_language: Language  # <--- Added
    # --------------------
    last_feedback: dict[str, Any] | None = None
    app_logo_src: str | None = None


class QuestionLoopStep(GameStep):
    def __init__(self, questions: list[Question], flow_title: str) -> None:
        super().__init__()
        self.questions = questions
        self.flow_title = flow_title
        self.index = 0
        self.feedback_mode = False
        self.last_result: dict[str, Any] | None = None

        # Default to PL, will update in enter()
        self.user_language: Language = Language.PL

        # UX State
        self.history: list[bool] = []
        self.current_streak = 0

    def enter(self, context: GameContext) -> None:
        super().enter(context)
        if "score" not in context.data:
            context.data["score"] = 0

        # --- LOCALIZATION SETUP ---
        # Fetch user profile to get language preference
        try:
            profile = context.repo.get_or_create_profile(context.user_id)
            self.user_language = profile.preferred_language
        except Exception as e:
            logger.error(f"Failed to fetch profile language: {e}")
            self.user_language = Language.PL
        # --------------------------

        logger.info(
            f"[QuestionLoopStep] Entered. User: {context.user_id}, Lang: {self.user_language}"
        )

    def _get_category_mastery(self, category: str) -> float:
        logger.info(f"[QuestionLoopStep] _get_category_mastery called for '{category}'")

        if not self.context:
            logger.error("[QuestionLoopStep] Context is None!")
            return 0.0

        try:
            val = self.context.repo.get_mastery_percentage(
                self.context.user_id, category
            )
            return val
        except Exception as e:
            logger.error(f"[QuestionLoopStep] Error fetching mastery: {e}")
            return 0.0

    def get_ui_model(self) -> UIModel:
        try:
            current_q = self.questions[self.index]

            # Calculate mastery
            cat_mastery = self._get_category_mastery(current_q.category)

            # Prepare history
            ui_history: list[bool | None] = [None] * len(self.questions)
            for i, result in enumerate(self.history):
                ui_history[i] = result

            payload = QuestionStepPayload(
                question=current_q,
                current_index=self.index + 1,
                total_count=len(self.questions),
                flow_title=self.flow_title,
                category_name=current_q.category,
                category_mastery=cat_mastery,
                session_history=ui_history,
                current_streak=self.current_streak,
                preferred_language=self.user_language,  # <--- Pass to UI
                last_feedback=self.last_result if self.feedback_mode else None,
            )

            ui_type = "FEEDBACK" if self.feedback_mode else "QUESTION"

            # --- DEMO MODE LOGIC ---
            branding_logo = None
            if self.context and self.context.is_demo_mode:
                branding_logo = GameConfig.get_demo_logo_path(
                    self.context.prospect_slug
                )

            return UIModel(
                type=ui_type,
                payload=payload,
                branding_logo_path=branding_logo,
            )

        except Exception as e:
            logger.critical(
                f"[QuestionLoopStep] CRASH in get_ui_model: {e}", exc_info=True
            )
            raise e

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        current_q = self.questions[self.index]

        if action == "SUBMIT_ANSWER":
            selected_option = payload
            is_correct = selected_option == current_q.correct_option

            if is_correct:
                context.data["score"] += 1
                self.current_streak += 1
            else:
                context.data["errors"].append(current_q.id)
                self.current_streak = 0

            self.history.append(is_correct)
            context.repo.save_attempt(context.user_id, current_q.id, is_correct)

            self.feedback_mode = True
            self.last_result = {
                "is_correct": is_correct,
                "selected": selected_option,
                "correct_option": current_q.correct_option,
                # Note: We don't pass 'explanation' string here anymore,
                # the UI will fetch the translated version from the Question object directly.
            }
            return None

        elif action == "NEXT_QUESTION":
            self.index += 1
            self.feedback_mode = False
            self.last_result = None

            if self.index >= len(self.questions):
                return "NEXT"

            return None

        return None
