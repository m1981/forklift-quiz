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
        assert self.current_screen_type == screen_type
        if title_contains:
            # Assuming payload has a title field for TEXT/SUMMARY steps
            assert title_contains in getattr(self.current_payload, "title", "")
        return self

    def click_next(self):
        """Simulates clicking the primary action button."""
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
