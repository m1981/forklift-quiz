import streamlit as st
import os
import logging
from src.repository import SQLiteQuizRepository
from src.service import QuizService
from src.viewmodel import QuizViewModel

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
    datefmt='%H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)

# 🔇 SILENCE THIRD-PARTY NOISE
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("fsevents").setLevel(logging.WARNING)

# --- Configuration ---
st.set_page_config(page_title="Warehouse Certification Quiz", layout="centered")

# CHANGED: Removed Standard, promoted Sprint to top
MODE_MAPPING = {
    "Codzienny Sprint (10 pytań)": "Daily Sprint",
    "Powtórka (Błędy)": "Review (Struggling Only)"
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
    logger.critical(f"🔥 System Crash: {e}", exc_info=True)
    st.error(f"System Error: {e}")
    st.stop()

apply_custom_styling()


# --- Sidebar Logic ---

def on_settings_change():
    """
    Callback: Wipes the current quiz session when User or Mode changes.
    """
    logger.info("🔄 STATE RESET: User changed settings. Clearing 'quiz_questions' to force reload.")
    st.session_state.quiz_questions = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.quiz_complete = False


def switch_to_sprint():
    """
    NEW CALLBACK: Forces the UI Mode widget to switch to Sprint (Default).
    """
    logger.info("🔀 SWITCH: User clicked 'Return to Learning'. Switching to Sprint Mode.")
    # Must match the key in MODE_MAPPING exactly
    st.session_state["ui_mode_selection"] = "Codzienny Sprint (10 pytań)"
    on_settings_change()


st.sidebar.header("Ustawienia")

user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"], key="user_id_selection",
                               on_change=on_settings_change)

ui_mode = st.sidebar.radio("Tryb", list(MODE_MAPPING.keys()), key="ui_mode_selection", on_change=on_settings_change)

if st.sidebar.button("Zeruj postęp"):
    logger.warning(f"🗑️ RESET: Manual progress reset triggered for {user_id}")
    vm.reset_progress(user_id)
    st.sidebar.success("Postęp wyzerowany.")
    st.rerun()

# --- Main Flow ---

# 1. Auto-Load Logic
if not vm.questions:
    service_mode = MODE_MAPPING.get(ui_mode, "Daily Sprint")  # Default to Sprint
    logger.info(f"📥 LOAD QUIZ: Mode='{service_mode}' | User='{user_id}'")
    vm.load_quiz(service_mode, user_id)
    logger.info(f"✅ LOADED: {len(vm.questions)} questions into session state.")

# 2. Dashboard Rendering
current_service_mode = MODE_MAPPING.get(ui_mode, "Daily Sprint")

if current_service_mode == "Daily Sprint":
    profile = vm.user_profile

    if profile:
        logger.info(
            f"📊 DASHBOARD: Rendering for {user_id}. DB says: Progress={profile.daily_progress} / Goal={profile.daily_goal}")
    else:
        logger.warning(f"📊 DASHBOARD: Profile is None for {user_id}!")

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
        st.button("Wróć do Nauki", on_click=switch_to_sprint, type="primary")
    elif "Sprint" in ui_mode:
        logger.info("ℹ️ STATE: Sprint mode empty.")
        st.balloons()
        st.success("🎉 Cel dzienny już zrealizowany!")
    else:
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

    if "Powtórka" in ui_mode:
        remaining_errors = len(vm.service.repo.get_incorrect_question_ids(user_id))
        if remaining_errors > 0:
            st.warning(f"⚠️ Pozostało jeszcze {remaining_errors} błędów do poprawy.")
            st.button(f"Poprawiaj dalej ({remaining_errors}) ➡️", on_click=on_settings_change, type="primary")
        else:
            st.balloons()
            st.success("🎉 Gratulacje! Wyczyściłeś wszystkie błędy!")
            st.button("Wróć do Nauki", on_click=switch_to_sprint, type="primary")
    else:
        st.balloons()
        st.success(f"✨ Sesja zakończona! Wynik: {st.session_state.score}/{len(vm.questions)}")
        st.button("Nowy start", on_click=on_settings_change, type="primary")

else:
    # --- QUIZ SCREEN ---
    q = vm.current_question
    logger.info(f"👀 RENDER: QID={q.id} | Index={st.session_state.current_index + 1}/{len(vm.questions)}")

    total_q = len(vm.questions)
    current_q = st.session_state.current_index + 1

    if "Powtórka" in ui_mode:
        st.caption(f"📝 Do poprawy: {current_q} z {total_q} błędów")
    elif "Sprint" in ui_mode:
        st.caption(f"🏃 Sprint: Pytanie {current_q} z {total_q}")

    st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path)

    # --- UPDATE 2: Add Hint Expander ---
    # Only show if a hint exists in the data
    if q.hint:
        with st.expander("💡 Potrzebujesz wskazówki?"):
            st.info(q.hint)

    st.write("")

    if not st.session_state.answer_submitted:
        for key, text in q.options.items():
            st.button(
                f"{key.value}) {text}",
                key=f"btn_{q.id}_{key}",
                on_click=vm.submit_answer,
                args=(user_id, key)
            )
    else:
        # STATE B: "Frozen" Result View (The Digest)
        # We render the options as text, coloring them based on results
        st.markdown("### Twoja odpowiedź:")

        user_selection = st.session_state.get('last_selected_option')

        for key, text in q.options.items():
            # Default style
            prefix = "⚪"
            style_start = ""
            style_end = ""

            # Logic for highlighting
            if key == q.correct_option:
                prefix = "✅" # Always mark the correct one
                style_start = ":green[**"
                style_end = "**]"
            elif key == user_selection:
                prefix = "❌" # Mark the user's wrong choice
                style_start = ":red[**"
                style_end = "**]"

            # Render the line
            st.markdown(f"{prefix} {style_start}{key.value}) {text}{style_end}")

        st.divider()

        # Feedback Section
        fb = st.session_state.last_feedback
        if fb:
            if fb['type'] == 'success':
                st.success(fb['msg'])
            else:
                st.error(fb['msg'])
            if fb.get('explanation'):
                st.info(f"ℹ️ **Wyjaśnienie:** {fb['explanation']}")

        if st.session_state.current_index < len(vm.questions) - 1:
            st.button("Następne ➡️", on_click=vm.next_question, type="primary")
        else:
            logger.info("🏁 UI: Showing 'Podsumowanie' button (Last Question).")
            st.button("Podsumowanie 🏁", on_click=lambda: None, type="primary")