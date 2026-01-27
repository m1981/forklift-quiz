# tests/drivers/game_driver.py
from src.game.director import GameDirector


class GameDriver:
    def __init__(self, director: GameDirector):
        self.director = director

    def _get_model(self):
        return self.director.get_ui_model()

    def assert_on_screen(self, expected_type: str, title_contains: str = None):
        model = self._get_model()
        assert model.type == expected_type, (
            f"Expected {expected_type}, got {model.type}"
        )

        if title_contains:
            payload = model.payload
            # Handle both 'title' (TextStep) and 'flow_title' (QuestionStep)
            title = getattr(payload, "title", getattr(payload, "flow_title", ""))
            assert title_contains in title, (
                f"Title '{title}' did not contain '{title_contains}'"
            )

        return self

    def click_next(self):
        self.director.handle_action("NEXT")
        return self

    def answer_question(self, option):
        self.director.handle_action("SUBMIT_ANSWER", option)
        return self

    def next_question(self):
        self.director.handle_action("NEXT_QUESTION")
        return self

    def finish_quiz(self):
        self.director.handle_action("FINISH")
        return self

    def review_mistakes(self):
        self.director.handle_action("REVIEW_MISTAKES")
        return self

    # --- THIS WAS MISSING ---
    def assert_score(self, expected_score: int):
        model = self._get_model()
        assert model.type == "SUMMARY", f"Expected SUMMARY, got {model.type}"
        assert model.payload.score == expected_score, (
            f"Expected score {expected_score}, got {model.payload.score}"
        )
        return self
