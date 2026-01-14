import streamlit as st
from src.game.core import GameContext
from src.game.director import GameDirector
from src.game.flows import DailySprintFlow, OnboardingFlow
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository

class GameViewModel:
    def __init__(self):
        if 'game_director' not in st.session_state:
            repo = SQLiteQuizRepository("data/quiz.db")
            user_id = "User1"
            context = GameContext(user_id=user_id, repo=repo)
            st.session_state.game_director = GameDirector(context)
            self.director: GameDirector = st.session_state.game_director

            # Now it is safe to call this
            self._check_auto_start(context)

        self.director: GameDirector = st.session_state.game_director

    def _check_auto_start(self, context: GameContext):
        profile = context.repo.get_or_create_profile(context.user_id)
        if not profile.has_completed_onboarding:
            self.director.start_flow(OnboardingFlow())
        else:
            # User is experienced -> Force Daily Sprint
            self.director.start_flow(DailySprintFlow())

    @property
    def ui_model(self):
        return self.director.get_ui_model()

    def start_daily_sprint(self):
        self.director.start_flow(DailySprintFlow())
        st.rerun()

    def start_onboarding(self):
        self.director.start_flow(OnboardingFlow())
        st.rerun()

    def handle_ui_action(self, action: str, payload=None):
        self.director.handle_action(action, payload)
        st.rerun()