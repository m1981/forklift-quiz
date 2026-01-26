# src/app.py

import logging
import sys

import pandas as pd
import streamlit as st

from src.config import GameConfig
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.presentation.renderer import StreamlitRenderer
from src.quiz.presentation.viewmodel import GameViewModel
from src.quiz.presentation.views.components import apply_styles

# --- 1. Configure Global Logging to Console ---
# Note: We configure this after imports to ensure all modules use this config,
# but imports are moved up to satisfy PEP8 (E402).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Force override of any existing config
)

# Setup
st.set_page_config(page_title="Kurs 2 WJO", layout="centered")
apply_styles()
vm = GameViewModel()
renderer = StreamlitRenderer()

# --- Sidebar Menu ---
st.sidebar.header("Nawigacja")

# 1. NEW: Dashboard Button (Home)
if st.sidebar.button("🏠 Pulpit", use_container_width=True):
    vm.navigate_to_dashboard()

st.sidebar.markdown("---")

# 2. Daily Sprint
if st.sidebar.button("🚀 Codzienny Sprint", type="primary", use_container_width=True):
    vm.start_daily_sprint()

st.sidebar.markdown("---")

# 3. Category Selection (Improved Logic)
st.sidebar.subheader("📚 Trening Tematyczny")

# We use a form or just a selectbox with a button.
# To make it feel "instant", we can check if the selection changed.
selected_cat = st.sidebar.selectbox(
    "Wybierz kategorię:", GameConfig.CATEGORIES, key="sidebar_cat_select"
)

# The button triggers the switch
if st.sidebar.button("Rozpocznij Trening", use_container_width=True):
    vm.start_category_mode(selected_cat)

st.sidebar.markdown("---")

# --- 🕵️‍♂️ DEBUG ZONE (NEW) ---
with st.sidebar.expander("🕵️‍♂️ QA / Debug Zone", expanded=False):
    st.markdown("### 1. Session Variables")
    # Show critical Python variables from the Director's Context
    if "game_director" in st.session_state:
        director = st.session_state.game_director
        if director.context:
            data = director.context.data
            st.write(f"**Score:** {data.get('score', 0)}")
            st.write(f"**Errors:** {len(data.get('errors', []))}")
            st.write(f"**Total Q:** {data.get('total_questions', 0)}")

    st.markdown("---")
    st.markdown("### 2. Database State")
    if st.button("📸 Snapshot DB"):
        # Fetch raw data
        repo = vm.director.context.repo
        user_id = vm.director.context.user_id
        # Cast to concrete type for debug method
        if isinstance(repo, SQLiteQuizRepository):
            rows = repo.debug_dump_user_progress(user_id)

            if rows:
                st.session_state["debug_db_rows"] = rows
            else:
                st.warning("No history found.")
        else:
            st.warning("Debug method only available for SQLite repository.")

    # Render the snapshot if it exists
    if "debug_db_rows" in st.session_state:
        df = pd.DataFrame(st.session_state["debug_db_rows"])
        st.dataframe(df, hide_index=True)

    st.markdown("---")
    if st.button("⚠️ RESET USER DB"):
        vm.director.context.repo.reset_user_progress(vm.director.context.user_id)
        st.success("User reset!")
        st.rerun()

# Main Render Loop
ui_data = vm.ui_model
renderer.render(ui_data, vm.handle_ui_action)
