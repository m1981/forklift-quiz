import os

import streamlit as st
from dotenv import load_dotenv

from src.config import GameConfig
from src.game.service import GameService
from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.seeder import DataSeeder
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.adapters.supabase_repository import SupabaseQuizRepository
from src.quiz.domain.ports import IQuizRepository
from src.quiz.presentation.views import dashboard_view, question_view, summary_view
from src.quiz.presentation.views.components import apply_styles

# --- CONFIGURATION ---
st.set_page_config(
    page_title=GameConfig.APP_TITLE,
    page_icon="🚜",
    layout="centered",
    initial_sidebar_state="collapsed",
)

load_dotenv()


def main() -> None:
    apply_styles()

    # --- 1. INITIALIZATION ---
    if "service" not in st.session_state:
        repo: IQuizRepository
        # Repo Setup
        if GameConfig.USE_SQLITE:
            db_manager = DatabaseManager("data/quiz.db")
            repo = SQLiteQuizRepository(db_manager)
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")

            # Explicit check to satisfy MyPy
            if url is None or key is None:
                st.error("Missing Supabase Credentials")
                st.stop()

            # Now MyPy knows url and key are definitely strings
            repo = SupabaseQuizRepository(url, key)

        # Seeding
        seeder = DataSeeder(repo)
        seeder.seed_if_empty()

        # Service & State
        st.session_state.service = GameService(repo)

        # --- FIX START: DEMO LOGIC ---
        # Check URL params for ?demo=tesla
        query_params = st.query_params
        demo_slug = query_params.get("demo")

        if demo_slug:
            # Use a unique ID for demo users so they don't mess up real stats
            st.session_state.user_id = f"demo_{demo_slug}"
            st.session_state.demo_slug = demo_slug  # Store for later use
        elif "user_id" not in st.session_state:
            st.session_state.user_id = "User1"
            st.session_state.demo_slug = None
        # --- FIX END ---

        # Routing Init
        profile = repo.get_or_create_profile(st.session_state.user_id)
        if not profile.has_completed_onboarding:
            st.session_state.service.start_onboarding(st.session_state.user_id)
        else:
            st.session_state.screen = "dashboard"

    # --- 2. ROUTING ---
    service = st.session_state.service
    user_id = st.session_state.user_id
    screen = st.session_state.get("screen", "dashboard")

    # Retrieve the slug we stored during init
    demo_slug = st.session_state.get("demo_slug")

    if screen == "dashboard":
        dashboard_view.render_dashboard_screen(service, user_id, demo_slug)

    elif screen == "quiz":
        question_view.render_quiz_screen(service, user_id)

    elif screen == "summary":
        summary_view.render_summary_screen(service, user_id)


if __name__ == "__main__":
    main()
