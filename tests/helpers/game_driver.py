from src.game.director import GameDirector


class GameDriver:
    def __init__(self, director: GameDirector):
        self.director = director

    @property
    def current_screen_type(self):
        return self.director.get_ui_model().type

    @property
    def current_payload(self):
        return self.director.get_ui_model().payload

    def assert_on_screen(self, screen_type: str, title_contains: str = None):
        """Asserts we are on the right screen."""
        assert self.current_screen_type == screen_type, (
            f"Expected screen '{screen_type}', but got '{self.current_screen_type}'"
        )

        if title_contains:
            # Handle different payload structures
            payload = self.current_payload
            # TextStep/SummaryStep use 'title' (implied or explicit),
            # QuestionStep uses 'flow_title'
            # Note: SummaryPayload doesn't strictly have a 'title' field,
            # but the view renders a hardcoded title.
            # For QuestionStepPayload, we check 'flow_title'.
            # For TextStepPayload, we check 'title'.

            actual_title = getattr(payload, "title", getattr(payload, "flow_title", ""))

            assert title_contains in actual_title, (
                f"Expected title containing '{title_contains}', got '{actual_title}'"
            )
        return self

    def click_next(self):
        """Simulates clicking the primary action button (TextStep)."""
        self.director.handle_action("NEXT")
        return self

    def answer_question(self, option_key):
        """Simulates answering a question."""
        self.director.handle_action("SUBMIT_ANSWER", option_key)
        return self

    def next_question(self):
        """Simulates clicking 'Next Question' after feedback."""
        self.director.handle_action("NEXT_QUESTION")
        return self

    # --- NEW METHODS ADDED BELOW ---

    def finish_quiz(self):
        """Simulates clicking 'Finish' on Summary."""
        self.director.handle_action("FINISH")
        return self

    def review_mistakes(self):
        """Simulates clicking 'Review Mistakes' on Summary."""
        self.director.handle_action("REVIEW_MISTAKES")
        return self

    def assert_score(self, expected_score: int):
        """Asserts the score on the Summary screen."""
        assert self.current_screen_type == "SUMMARY", "Not on Summary screen"
        assert self.current_payload.score == expected_score, (
            f"Expected score {expected_score}, got {self.current_payload.score}"
        )
        return self
