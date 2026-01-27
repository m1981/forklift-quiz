from typing import Any

import streamlit as st

from src.game.core import GameContext, UIModel
from src.game.director import GameDirector
from src.game.flows import CategorySprintFlow, DailySprintFlow, OnboardingFlow
from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.seeder import DataSeeder
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository


class GameViewModel:
    def __init__(self) -> None:
        if "game_director" not in st.session_state:
            # --- COMPOSITION ROOT START ---
            # 1. Initialize Infrastructure
            db_manager = DatabaseManager("data/quiz.db")

            # 2. Initialize Repository
            repo = SQLiteQuizRepository(db_manager)

            # 3. Run Seeder (Application Logic)
            seeder = DataSeeder(repo)
            seeder.seed_if_empty()

            # 4. Initialize Game Context
            user_id = "User1"  # In real app, get from auth
            context = GameContext(user_id=user_id, repo=repo)

            # 5. Initialize Director
            st.session_state.game_director = GameDirector(context)
            # --- COMPOSITION ROOT END ---

            self.director: GameDirector = st.session_state.game_director
            self._check_auto_start(context)

        self.director = st.session_state.game_director

    def _check_auto_start(self, context: GameContext) -> None:
        profile = context.repo.get_or_create_profile(context.user_id)
        if not profile.has_completed_onboarding:
            self.director.start_flow(OnboardingFlow())

    @property
    def ui_model(self) -> UIModel | None:
        return self.director.get_ui_model()

    def start_daily_sprint(self) -> None:
        self.director.start_flow(DailySprintFlow())
        st.rerun()

    def start_category_mode(self, category: str) -> None:
        self.director.start_flow(CategorySprintFlow(category))
        st.rerun()

    def start_onboarding(self) -> None:
        self.director.start_flow(OnboardingFlow())
        st.rerun()

    def handle_ui_action(self, action: str, payload: Any = None) -> None:
        if action == "START_SPRINT_MANUAL":
            self.start_daily_sprint()
            return
        if action == "START_ONBOARDING_MANUAL":
            self.start_onboarding()
            return
        if action == "START_CATEGORY_MANUAL":
            self.start_category_mode(payload)
            return
        if action == "NAVIGATE_HOME":
            self.navigate_to_dashboard()
            return

        self.director.handle_action(action, payload)
        st.rerun()

    def navigate_to_dashboard(self) -> None:
        """Forcefully clears the current flow to show the Dashboard."""
        self.director._current_step = None
        self.director._queue = []
        self.director._is_complete = True
        st.rerun()
