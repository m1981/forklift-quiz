from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Union

from src.quiz.domain.ports import IQuizRepository


@dataclass
class GameContext:
    """
    Shared state passed between steps in a flow.
    Acts as a 'Blackboard' for the current session.
    """

    user_id: str
    repo: IQuizRepository
    # Generic storage for score, flags, etc.
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class UIModel:
    """
    Data Transfer Object (DTO) describing WHAT to render.
    The View layer will decide HOW to render it (Streamlit, Console, etc).
    """

    type: str  # e.g., 'TEXT', 'QUESTION', 'SUMMARY'
    payload: Any


class GameStep(ABC):
    def __init__(self) -> None:
        self.context: GameContext | None = None

    def enter(self, context: GameContext) -> None:
        """Lifecycle hook. Stores context by default."""
        self.context = context

    @abstractmethod
    def get_ui_model(self) -> UIModel:
        """Returns the data needed to render the current screen."""
        pass

    @abstractmethod
    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        """
        Process user input.
        Returns:
            - None: Stay on current step.
            - "NEXT": Advance to next step in queue.
            - GameStep instance: Inject a new step (branching).
        """
        pass


class GameFlow(ABC):
    """
    A Scenario Factory. Defines the sequence of steps.
    """

    @abstractmethod
    def build_steps(self, context: GameContext) -> list[GameStep]:
        pass
