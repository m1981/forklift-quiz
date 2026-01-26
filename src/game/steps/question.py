from dataclasses import dataclass
from typing import Any, Union

from src.game.core import GameContext, GameStep, UIModel
from src.quiz.domain.models import Question


@dataclass
class QuestionStepPayload:
    question: Question
    current_index: int
    total_count: int
    # --- NEW FIELDS ---
    flow_title: str  # e.g. "Codzienny Sprint"
    category_name: str  # e.g. "Napęd i Zasilanie"
    category_mastery: float  # 0.0 to 1.0
    # ------------------
    last_feedback: dict[str, Any] | None = None


class QuestionLoopStep(GameStep):
    def __init__(self, questions: list[Question], flow_title: str) -> None:
        super().__init__()
        self.questions = questions
        self.flow_title = flow_title  # Store the context name
        self.index = 0
        self.feedback_mode = False
        self.last_result: dict[str, Any] | None = None

    def enter(self, context: GameContext) -> None:
        super().enter(context)
        # Initialize score in the shared context if not present
        if "score" not in context.data:
            context.data["score"] = 0
        if "errors" not in context.data:
            context.data["errors"] = []

    def _get_category_mastery(self, category: str) -> float:
        if not self.context:
            return 0.0
        # Delegate purely to the repo
        return self.context.repo.get_mastery_percentage(self.context.user_id, category)

    def get_ui_model(self) -> UIModel:
        current_q = self.questions[self.index]

        # Calculate mastery for this specific question's category
        # (In Daily Sprint, this will change per question, which is great context)
        cat_mastery = self._get_category_mastery(current_q.category)

        payload = QuestionStepPayload(
            question=current_q,
            current_index=self.index + 1,
            total_count=len(self.questions),
            flow_title=self.flow_title,  # <--- Pass Context
            category_name=current_q.category,  # <--- Pass Category
            category_mastery=cat_mastery,  # <--- Pass Stats
            last_feedback=self.last_result if self.feedback_mode else None,
        )

        # We use different UI types to tell the View how to render
        ui_type = "FEEDBACK" if self.feedback_mode else "QUESTION"
        return UIModel(type=ui_type, payload=payload)

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        current_q = self.questions[self.index]

        if action == "SUBMIT_ANSWER":
            selected_option = payload
            is_correct = selected_option == current_q.correct_option

            if is_correct:
                context.data["score"] += 1
            else:
                context.data["errors"].append(current_q.id)

            # 2. Persist to DB (Side Effect)
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
                return "NEXT"  # Exit this step

            return None  # Stay on this step (show next question)

        return None
