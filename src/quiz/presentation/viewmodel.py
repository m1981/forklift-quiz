import os
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from src.game.core import GameContext, UIModel
from src.game.director import GameDirector
from src.game.flows import CategorySprintFlow, DailySprintFlow, OnboardingFlow
from src.quiz.adapters.seeder import DataSeeder
from src.quiz.adapters.supabase_repository import SupabaseQuizRepository

# Load environment variables (SUPABASE_URL, SUPABASE_KEY)
load_dotenv()


class GameViewModel:
    def __init__(self) -> None:
        if "game_director" not in st.session_state:
            # --- COMPOSITION ROOT START ---

            # 1. Initialize Infrastructure (Supabase)
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")

            if not url or not key:
                st.error("Configuration Error: Missing Supabase Credentials in .env")
                st.stop()

            repo = SupabaseQuizRepository(url, key)

            # 2. Run Seeder (Application Logic)
            # This will check Supabase. If empty, it reads local JSON and uploads.
            seeder = DataSeeder(repo)
            seeder.seed_if_empty()

            # 3. Initialize Game Context
            # TODO: In Phase 2, this comes from Auth0
            user_id = "User1"
            context = GameContext(user_id=user_id, repo=repo)

            # 4. Initialize Director
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
