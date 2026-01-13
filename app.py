import streamlit as st
import logging

# Import Adapters & Core
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.presentation.state_provider import StreamlitStateProvider
from src.quiz.application.service import QuizService
from src.quiz.presentation.viewmodel import QuizViewModel
from src.quiz.presentation.views import components, question_view, summary_view
from src.fsm import QuizState

# --- 1. Bootstrap Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


# --- 2. Dependency Injection (Composition Root) ---
@st.cache_resource
def get_service():
    # Infrastructure
    repo = SQLiteQuizRepository("data/quiz.db")
    # Application
    return QuizService(repo)


def main():
    st.set_page_config(page_title="Warehouse Quiz", layout="centered")
    components.apply_styles()

    # Wiring
    service = get_service()
    state_provider = StreamlitStateProvider()
    vm = QuizViewModel(service, state_provider)

    # --- 3. Sidebar & Global State ---
    # We get current state from VM to pre-select UI options
    current_user = state_provider.get('user_id', 'Daniel')
    current_mode = state_provider.get('current_mode', 'Daily Sprint')

    sel_user, sel_mode, do_reset = components.render_sidebar(current_user, current_mode)

    # Handle Sidebar Actions
    if do_reset:
        service.repository.reset_user_progress(sel_user)
        vm.reset()
        st.rerun()

    if sel_user != current_user or sel_mode != current_mode:
        vm.reset()  # Reset if settings change
        # We don't start immediately; we wait for user to click "Start" in IDLE state
        state_provider.set('user_id', sel_user)
        state_provider.set('current_mode', sel_mode)
        st.rerun()

    # --- 4. Main Router (FSM) ---
    state = vm.current_state

    if state == QuizState.IDLE:
        st.title("🎓 Warehouse Certification")
        st.info(f"Gotowy, {sel_user}?")
        if st.button("🚀 Start Quiz", type="primary"):
            vm.start_quiz(sel_mode, sel_user)
            st.rerun()

    elif state == QuizState.LOADING:
        with st.spinner("Ładowanie pytań..."):
            pass

    elif state == QuizState.QUESTION_ACTIVE:
        components.render_dashboard(vm.get_dashboard_config())
        question_view.render_active(vm)

    elif state == QuizState.FEEDBACK_VIEW:
        components.render_dashboard(vm.get_dashboard_config())
        question_view.render_feedback(vm)

    elif state == QuizState.SUMMARY:
        summary_view.render(vm)

    elif state == QuizState.EMPTY_STATE:
        st.warning("Brak pytań w tym trybie.")
        if st.button("Wróć"):
            vm.reset()
            st.rerun()


if __name__ == "__main__":
    main()