from dataclasses import dataclass
from typing import Any, Union

from src.game.core import GameContext, GameStep, UIModel


@dataclass
class TextStepPayload:
    title: str
    content: str
    button_text: str
    image_path: str | None = None


class TextStep(GameStep):
    """
    Displays a static screen with text and a 'Next' button.
    Useful for: Onboarding, Story segments, Level transitions.
    """

    def __init__(
        self,
        title: str,
        content: str,
        button_text: str = "Dalej",
        image_path: str | None = None,
    ) -> None:
        super().__init__()
        self.payload = TextStepPayload(title, content, button_text, image_path)

    def enter(self, context: GameContext) -> None:
        super().enter(context)

    def get_ui_model(self) -> UIModel:
        return UIModel(type="TEXT", payload=self.payload)

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        if action == "NEXT":
            return "NEXT"
        return None
