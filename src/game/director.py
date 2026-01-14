import logging
from typing import List, Optional, Any
from src.game.core import GameContext, GameFlow, GameStep, UIModel
from src.shared.telemetry import measure_time

logger = logging.getLogger(__name__)


class GameDirector:
    def __init__(self, context: GameContext):
        self.context = context
        self._queue: List[GameStep] = []
        self._current_step: Optional[GameStep] = None
        self._is_complete = False

    @property
    def is_complete(self) -> bool:
        return self._is_complete

    @measure_time("director_start_flow")
    def start_flow(self, flow: GameFlow):
        """Initializes a new scenario."""
        logger.info(f"🎬 Director: Starting Flow {flow.__class__.__name__}")
        self._queue = flow.build_steps(self.context)
        self._is_complete = False
        self._advance()

    def get_ui_model(self) -> Optional[UIModel]:
        """Returns the data for the View to render."""
        if self._is_complete:
            return UIModel(type="EMPTY", payload={"message": "Flow Complete"})

        if self._current_step:
            return self._current_step.get_ui_model()

        return UIModel(type="LOADING", payload={})

    @measure_time("director_handle_action")
    def handle_action(self, action: str, payload: Any = None):
        """Central input handler."""
        if not self._current_step:
            logger.warning("⚠️ Director: Action received but no active step.")
            return

        logger.info(f"🎮 Action: {action} | Step: {self._current_step.__class__.__name__}")

        # Delegate logic to the specific step
        result = self._current_step.handle_action(action, payload, self.context)

        if result == "NEXT":
            self._advance()
        elif isinstance(result, GameStep):
            # Dynamic Branching: Insert new step at the front
            logger.info(f"🔀 Branching to {result.__class__.__name__}")
            self._queue.insert(0, result)
            self._advance()

    def _advance(self):
        """Moves to the next step in the queue."""
        if self._queue:
            self._current_step = self._queue.pop(0)
            logger.info(f"➡️ Entering Step: {self._current_step.__class__.__name__}")
            self._current_step.enter(self.context)
        else:
            logger.info("🏁 Flow Finished")
            self._current_step = None
            self._is_complete = True