import streamlit as st
from src.game.core import GameContext
from src.game.director import GameDirector
from src.game.flows import DailySprintFlow, OnboardingFlow
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository


class GameViewModel:
    def __init__(self):
        # 1. Initialize Infrastructure
        if 'game_director' not in st.session_state:
            repo = SQLiteQuizRepository("data/quiz.db")
            # We use a dummy user for now, or fetch from sidebar
            context = GameContext(user_id="User1", repo=repo)
            st.session_state.game_director = GameDirector(context)

        self.director: GameDirector = st.session_state.game_director

    @property
    def ui_model(self):
        return self.director.get_ui_model()

    def start_daily_sprint(self):
        self.director.start_flow(DailySprintFlow())

    def start_onboarding(self):
        self.director.start_flow(OnboardingFlow())

    def handle_ui_action(self, action: str, payload=None):
        """
        Called by the View when a button is clicked.
        """
        self.director.handle_action(action, payload)
        # No need to manually persist; director state is in st.session_state