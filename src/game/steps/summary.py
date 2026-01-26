from dataclasses import dataclass
from typing import Any, Union

from src.game.core import GameContext, GameStep, UIModel
from src.shared.telemetry import Telemetry


@dataclass
class SummaryPayload:
    score: int
    total: int
    message: str
    has_errors: bool


class SummaryStep(GameStep):
    def enter(self, context: GameContext) -> None:
        super().enter(context)

    def get_ui_model(self) -> UIModel:
        if not self.context:
            raise RuntimeError("SummaryStep accessed before enter() called")

        # Read data from the Blackboard (Context)
        score = self.context.data.get("score", 0)

        # We need to know total questions.
        total = self.context.data.get("total_questions", 0)
        errors = self.context.data.get("errors", [])

        return UIModel(
            type="SUMMARY",
            payload=SummaryPayload(
                score=score,
                total=total,
                message="Quiz Finished",
                has_errors=len(errors) > 0,
            ),
        )

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        if action == "FINISH":
            return "NEXT"

        if action == "REVIEW_MISTAKES":
            # Import locally to avoid circular dependency
            from src.game.steps.question import QuestionLoopStep

            # <--- LOGIC: Branching
            # We return a NEW QuestionLoopStep containing only the failed questions
            error_ids = context.data.get("errors", [])

            # Telemetry for debugging
            Telemetry("SummaryStep").log_info(
                "Review Request", found_ids_count=len(error_ids), ids=str(error_ids)
            )

            if not error_ids:
                return "NEXT"

            # Fetch the actual question objects for the errors
            review_questions = context.repo.get_questions_by_ids(error_ids)

            # Clear errors from context so we don't loop forever
            context.data["errors"] = []

            # --- FIX: Added flow_title ---
            return QuestionLoopStep(review_questions, flow_title="🛠️ Poprawa Błędów")

        return None
