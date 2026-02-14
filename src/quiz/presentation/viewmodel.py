import os
import uuid
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from src.config import GameConfig
from src.game.core import GameContext, UIModel
from src.game.director import GameDirector
from src.game.flows import CategorySprintFlow, DailySprintFlow, DemoFlow, OnboardingFlow
from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.seeder import DataSeeder
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.adapters.supabase_repository import SupabaseQuizRepository
from src.quiz.domain.ports import IQuizRepository

# Load environment variables (SUPABASE_URL, SUPABASE_KEY)
load_dotenv()


class GameViewModel:
    def __init__(self) -> None:
        if "game_director" not in st.session_state:
            # --- COMPOSITION ROOT START ---

            # 1. Initialize Infrastructure (SQLite vs Supabase)
            repo: IQuizRepository  # Type annotation for the variable

            if GameConfig.USE_SQLITE:
                # Local Development Mode
                db_manager = DatabaseManager("data/quiz.db")
                repo = SQLiteQuizRepository(db_manager)
                st.toast("🛠️ Running in SQLite Mode", icon="💾")
            else:
                # Production / Cloud Mode
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY")
                if not url or not key:
                    st.error("Missing Supabase Credentials")
                    st.stop()
                repo = SupabaseQuizRepository(url, key)

            # 2. Run Seeder
            seeder = DataSeeder(repo)
            seeder.seed_if_empty()

            # 3. Initialize Game Context & Identity Logic
            # --- DEMO MODE LOGIC ---
            query_params = st.query_params
            demo_slug = query_params.get("demo")
            demo_lang = query_params.get("lang")  # e.g. "en"

            if demo_slug:
                if "demo_user_id" not in st.session_state:
                    st.session_state.demo_user_id = str(uuid.uuid4())

                user_id = st.session_state.demo_user_id
                is_demo = True

                profile = repo.get_or_create_profile(user_id)
                profile.metadata = {"type": "demo", "prospect": demo_slug}
                profile.demo_prospect_slug = demo_slug  # NEW: Set first-class field
                repo.save_profile(profile)

                # 4. FORCE LANGUAGE UPDATE if param is present
                # This ensures ?lang=en overrides whatever is in DB
                if demo_lang:
                    try:
                        from src.quiz.domain.models import Language

                        new_lang = Language(demo_lang)
                        if profile.preferred_language != new_lang:
                            profile.preferred_language = new_lang
                            repo.save_profile(profile)  # <--- SAVE IMMEDIATELY
                            st.toast(f"Language set to: {new_lang.value}")
                    except ValueError:
                        pass  # Invalid lang code, ignore

                # If no param, we keep whatever is in DB (persistence)

            else:
                user_id = "User1"
                is_demo = False
                demo_slug = None

            context = GameContext(
                user_id=user_id,
                repo=repo,
                is_demo_mode=is_demo,
                prospect_slug=demo_slug,
            )

            # 4. Initialize Director
            st.session_state.game_director = GameDirector(context)
            # --- COMPOSITION ROOT END ---

            self.director: GameDirector = st.session_state.game_director
            self._check_auto_start(context)

        self.director = st.session_state.game_director

    def _check_auto_start(self, context: GameContext) -> None:
        # --- DEMO FLOW TRIGGER ---
        if context.is_demo_mode:
            # Always force Demo Flow, ignore onboarding status
            self.director.start_flow(DemoFlow())
            return

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
