# src/game/steps/question.py

import logging
from dataclasses import dataclass
from typing import Any, Union

from src.game.core import GameContext, GameStep, UIModel
from src.quiz.domain.models import Question

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
    session_history: list[bool | None]  # True=Correct, False=Wrong, None=Future
    current_streak: int
    # -------------------------
    last_feedback: dict[str, Any] | None = None


class QuestionLoopStep(GameStep):
    def __init__(self, questions: list[Question], flow_title: str) -> None:
        super().__init__()
        self.questions = questions
        self.flow_title = flow_title
        self.index = 0
        self.feedback_mode = False
        self.last_result: dict[str, Any] | None = None

        # UX State
        self.history: list[bool] = []  # Stores results of answered questions
        self.current_streak = 0  # Tracks consecutive correct answers in this session

    def enter(self, context: GameContext) -> None:
        super().enter(context)
        if "score" not in context.data:
            context.data["score"] = 0

        # TELEMETRY: Log entry
        logger.info(f"[QuestionLoopStep] Entered. Context User: {context.user_id}")

    # --- RESTORED MISSING METHOD ---
    def _get_category_mastery(self, category: str) -> float:
        # TELEMETRY: Log this call to prove the method exists and is called
        logger.info(f"[QuestionLoopStep] _get_category_mastery called for '{category}'")

        if not self.context:
            logger.error(
                "[QuestionLoopStep] Context is None inside _get_category_mastery!"
            )
            return 0.0

        try:
            val = self.context.repo.get_mastery_percentage(
                self.context.user_id, category
            )
            logger.info(f"[QuestionLoopStep] Repo returned mastery: {val}")
            return val
        except Exception as e:
            logger.error(f"[QuestionLoopStep] Error fetching mastery: {e}")
            return 0.0

    def get_ui_model(self) -> UIModel:
        try:
            current_q = self.questions[self.index]
            logger.info(
                f"[QuestionLoopStep] Preparing UI for Question Index "
                f"{self.index} (ID: {current_q.id})"
            )

            # Calculate mastery
            # This is where the previous error happened
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
                last_feedback=self.last_result if self.feedback_mode else None,
            )

            ui_type = "FEEDBACK" if self.feedback_mode else "QUESTION"
            return UIModel(type=ui_type, payload=payload)

        except Exception as e:
            logger.critical(
                f"[QuestionLoopStep] CRASH in get_ui_model: {e}", exc_info=True
            )
            raise e

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        current_q = self.questions[self.index]

        logger.info(f"[QuestionLoopStep] Handling Action: {action}")

        if action == "SUBMIT_ANSWER":
            selected_option = payload
            is_correct = selected_option == current_q.correct_option

            if is_correct:
                context.data["score"] += 1
                self.current_streak += 1
            else:
                context.data["errors"].append(current_q.id)
                self.current_streak = 0  # Reset streak on error (High stakes!)

            # Update History
            self.history.append(is_correct)

            context.repo.save_attempt(context.user_id, current_q.id, is_correct)

            # 3. Set Feedback State
            self.feedback_mode = True
            self.last_result = {
                "is_correct": is_correct,
                "selected": selected_option,
                "correct_option": current_q.correct_option,
                "explanation": current_q.explanation,
            }
            return None  # Stay on this step to show feedback

        elif action == "NEXT_QUESTION":
            # Advance index
            self.index += 1
            self.feedback_mode = False
            self.last_result = None

            # Check if loop is finished
            if self.index >= len(self.questions):
                logger.info("[QuestionLoopStep] Loop finished. Returning NEXT.")
                return "NEXT"

            return None  # Stay on this step (show next question)

        return None
