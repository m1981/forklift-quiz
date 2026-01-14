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

            # Assign self.director BEFORE calling _check_auto_start
            self.director: GameDirector = st.session_state.game_director

            # Auto-Start Logic
            self._check_auto_start(context)

        self.director: GameDirector = st.session_state.game_director

    def _check_auto_start(self, context: GameContext):
        profile = context.repo.get_or_create_profile(context.user_id)
        if not profile.has_completed_onboarding:
            self.director.start_flow(OnboardingFlow())
        # Note: We REMOVED the auto-start for Daily Sprint here.
        # Why? Because if the user refreshes the page after finishing a sprint,
        # we don't want to force them into a new one immediately.
        # We let them see the "Empty" state (Dashboard) instead.

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
        # <--- NEW HANDLERS
        if action == "START_SPRINT_MANUAL":
            self.start_daily_sprint()
            return
        if action == "START_ONBOARDING_MANUAL":
            self.start_onboarding()
            return

        self.director.handle_action(action, payload)
        st.rerun()