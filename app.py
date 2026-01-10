import streamlit as st
import os
import logging
from src.repository import SQLiteQuizRepository
from src.service import QuizService
from src.viewmodel import QuizViewModel

# --- Logging Configuration ---
# We add a custom handler to ensure logs appear in your terminal immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- Configuration ---
st.set_page_config(page_title="Warehouse Certification Quiz", layout="centered")

MODE_MAPPING = {
    "Nauka (Standard)": "Standard",
    "Powtórka (Błędy)": "Review (Struggling Only)",
    "Codzienny Sprint (10 pytań)": "Daily Sprint"
}


# --- Custom CSS ---
def apply_custom_styling():
    st.markdown("""
        <style>
            .block-container { padding-top: 3rem !important; padding-bottom: 1rem !important; }
            .question-text { font-size: 1.1rem !important; font-weight: 600; line-height: 1.4; margin-bottom: 10px; color: #31333F; }
            .stButton button { text-align: left !important; padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
            .stat-box { padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin-bottom: 10px; text-align: center; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)


# --- Dependency Injection ---
@st.cache_resource
def get_viewmodel():
    logger.info("🔌 Bootstrapping Application (Service & Repository)...")
    repo = SQLiteQuizRepository(db_path="data/quiz.db")
    service = QuizService(repo)
    seed_file = "data/seed_questions.json"
    if os.path.exists(seed_file):
        service.initialize_db_from_file(seed_file)
    return QuizViewModel(service)


try:
    vm = get_viewmodel()
    vm.ensure_state_initialized()
except Exception as e:
    logger.critical(f"🔥 System Crash: {e}")
    st.error(f"System Error: {e}")
    st.stop()

apply_custom_styling()

# --- Sidebar ---
st.sidebar.header("Ustawienia")


def on_settings_change():
    """
    Callback: Wipes the current quiz session when User or Mode changes.
    """
    logger.info("🔄 STATE RESET: User changed settings. Clearing 'quiz_questions' to force reload.")

    # Debug Dump (Optional)
    try:
        repo = SQLiteQuizRepository(db_path="data/quiz.db")
        # We access the session state key directly here
        current_user = st.session_state.get("user_id_selection", "Daniel")
        repo.debug_dump_user_state(current_user)
    except Exception as e:
        print(f"Debug dump failed: {e}")

    st.session_state.quiz_questions = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.quiz_complete = False

# Update the selectbox to store the key so we can access it
user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"], key="user_id_selection", on_change=on_settings_change)
ui_mode = st.sidebar.radio("Tryb", list(MODE_MAPPING.keys()), on_change=on_settings_change)

if st.sidebar.button("Zeruj postęp"):
    logger.warning(f"🗑️ RESET: Manual progress reset triggered for {user_id}")
    vm.reset_progress(user_id)
    st.sidebar.success("Postęp wyzerowany.")
    st.rerun()

# --- Main Flow ---

# 1. Auto-Load Logic (The "Brain" of the page load)
if not vm.questions:
    service_mode = MODE_MAPPING.get(ui_mode, "Standard")
    logger.info(f"📥 LOAD QUIZ: Mode='{service_mode}' | User='{user_id}'")

    vm.load_quiz(service_mode, user_id)

    logger.info(f"✅ LOADED: {len(vm.questions)} questions into session state.")

# 2. Dashboard Rendering (CONTEXT AWARE FIX)
# We determine the internal mode string
current_service_mode = MODE_MAPPING.get(ui_mode, "Standard")

# FIX: Only show Gamification Dashboard in "Growth" modes (Standard & Sprint).
# Hide it in "Maintenance" mode (Review) to reduce clutter and confusion.
if current_service_mode in ["Standard", "Daily Sprint"]:
    profile = vm.user_profile
    if profile:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div class="stat-box">🔥 Seria: {profile.streak_days} dni</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-box">🎯 Cel Dzienny: {profile.daily_progress}/{profile.daily_goal}</div>',
                        unsafe_allow_html=True)

    daily_pct = min(profile.daily_progress / profile.daily_goal, 1.0)
    st.progress(daily_pct)

    if profile.daily_progress >= profile.daily_goal:
        st.success("🎉 Cel dzienny osiągnięty! Wszystko co robisz teraz to Twój dodatkowy sukces!")

        st.divider()
else:
    st.caption("🛠️ Tryb Poprawy Błędów")
    st.divider()

# 3. Content Rendering
if not vm.questions:
    if "Powtórka" in ui_mode:
        logger.info("ℹ️ STATE: Review mode empty (User has 0 incorrect answers).")
        st.info("🎉 Brak błędów do poprawy!")
    elif "Sprint" in ui_mode:
        logger.info("ℹ️ STATE: Sprint mode empty (Goal met).")
        st.balloons()
        st.success("🎉 Cel dzienny już zrealizowany!")
    else:
        logger.error("❌ STATE: Standard mode returned 0 questions. Check DB/Seed file.")
        st.error("Brak pytań w bazie.")

elif vm.is_complete and st.session_state.answer_submitted:
    # --- SUMMARY SCREEN ---
    logger.info(f"🏁 END SCREEN: Score={st.session_state.score}/{len(vm.questions)}")

    fb = st.session_state.last_feedback
    if fb:
        if fb['type'] == 'success':
            st.success(fb['msg'])
        else:
            st.error(fb['msg'])
        if fb['explanation']: st.info(f"ℹ️ **Wyjaśnienie:** {fb['explanation']}")

    st.markdown("---")

    # --- NEW LOGIC: Smart Loop for Review Mode ---
    if "Powtórka" in ui_mode:
        # Check if there are ANY incorrect questions left in the DB
        # We access the repo directly via the service to check the count
        remaining_errors = len(vm.service.repo.get_incorrect_question_ids(user_id))

        if remaining_errors > 0:
            st.warning(f"⚠️ Pozostało jeszcze {remaining_errors} błędów do poprawy.")
            # The button triggers 'on_settings_change' which clears state -> triggers auto-reload -> fetches remaining errors
            st.button(f"Poprawiaj dalej ({remaining_errors}) ➡️", on_click=on_settings_change, type="primary")
        else:
            st.balloons()
            st.success("🎉 Gratulacje! Wyczyściłeś wszystkie błędy!")
            st.button("Wróć do Nauki", on_click=on_settings_change)

    else:
        # Standard behavior for other modes
        st.balloons()
        st.success(f"✨ Sesja zakończona! Wynik: {st.session_state.score}/{len(vm.questions)}")
        st.button("Nowy start", on_click=on_settings_change, type="primary")

else:
    # --- QUIZ SCREEN ---
    q = vm.current_question

    # Debug Log: Verify what question is being shown
    logger.info(f"👀 RENDER: QID={q.id} | Index={st.session_state.current_index + 1}/{len(vm.questions)}")

    # Progress Text
    total_q = len(vm.questions)
    current_q = st.session_state.current_index + 1

    if "Powtórka" in ui_mode:
        st.caption(f"📝 Do poprawy: {current_q} z {total_q} błędów")
    elif "Sprint" in ui_mode:
        st.caption(f"🏃 Sprint: Pytanie {current_q} z {total_q}")
    else:
        st.caption(f"📚 Baza pytań: {current_q} z {total_q}")

    # Question Text
    st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path)
    st.write("")

    # Interaction
    if not st.session_state.answer_submitted:
        for key, text in q.options.items():
            st.button(
                f"{key.value}) {text}",
                key=f"btn_{q.id}_{key}",
                on_click=vm.submit_answer,
                args=(user_id, key)
            )
    else:
        # Feedback
        fb = st.session_state.last_feedback
        if fb:
            if fb['type'] == 'success':
                st.success(fb['msg'])
            else:
                st.error(fb['msg'])
            if fb['explanation']: st.info(f"ℹ️ **Wyjaśnienie:** {fb['explanation']}")

        if st.session_state.current_index < len(vm.questions) - 1:
            st.button("Następne ➡️", on_click=vm.next_question, type="primary")
        else:
            logger.info("🏁 UI: Showing 'Podsumowanie' button (Last Question).")
            st.button("Podsumowanie 🏁", on_click=lambda: None, type="primary")