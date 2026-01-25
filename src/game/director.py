import logging
from typing import Any

from src.game.core import GameContext, GameFlow, GameStep, UIModel
from src.shared.telemetry import Telemetry, measure_time

logger = logging.getLogger(__name__)


class GameDirector:
    def __init__(self, context: GameContext) -> None:
        self.context = context
        self._queue: list[GameStep] = []
        self._current_step: GameStep | None = None
        self._is_complete: bool = False
        self.telemetry = Telemetry("GameDirector")

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @measure_time("director_start_flow")
    def start_flow(self, flow: GameFlow) -> None:
        """Initializes a new scenario."""
        flow_name = flow.__class__.__name__
        self.telemetry.log_info(f"🎬 Starting Flow: {flow_name}")
        self._queue = flow.build_steps(self.context)
        self._is_complete = False
        self._advance()

    def get_ui_model(self) -> UIModel | None:
        """Returns the data for the View to render."""

        # 1. Active Step
        if self._current_step:
            return self._current_step.get_ui_model()

        # 2. No Active Step (Idle or Finished)
        self.telemetry.log_info("No active step. Returning EMPTY state (Dashboard).")
        return UIModel(type="EMPTY", payload={"message": "Ready"})

    @measure_time("director_handle_action")
    def handle_action(self, action: str, payload: Any = None) -> None:
        """Central input handler."""
        if not self._current_step:
            self.telemetry.log_error(
                "Action received but no active step", Exception("No Active Step")
            )
            return

        step_name = self._current_step.__class__.__name__
        self.telemetry.log_info(
            f"🎮 Action: {action}", step=step_name, payload=str(payload)
        )

        # Delegate logic to the specific step
        result = self._current_step.handle_action(action, payload, self.context)

        if result == "NEXT":
            self._advance()
        elif isinstance(result, GameStep):
            # Dynamic Branching: Insert new step at the front
            self.telemetry.log_info(f"🔀 Branching to {result.__class__.__name__}")
            self._queue.insert(0, result)
            self._advance()

    def _advance(self) -> None:
        """Moves to the next step in the queue."""
        if self._queue:
            self._current_step = self._queue.pop(0)
            step_name = self._current_step.__class__.__name__
            self.telemetry.log_info(f"➡️ Entering Step: {step_name}")
            self._current_step.enter(self.context)
        else:
            self.telemetry.log_info("🏁 Flow Finished")
            self._current_step = None
            self._is_complete = True
