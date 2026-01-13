import streamlit as st
import os
import logging
from src.repository import SQLiteQuizRepository
from src.service import QuizService
from src.viewmodel import QuizViewModel
from src.fsm import QuizState

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(message)s',
    datefmt='%H:%M:%S',
    force=True
)
logger = logging.getLogger(__name__)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# --- Configuration ---
st.set_page_config(page_title="Warehouse Certification Quiz", layout="centered")


# --- Dependency Injection ---
@st.cache_resource
def get_quiz_service():
    logger.info("🔌 Bootstrapping Service & Repository...")
    repo = SQLiteQuizRepository(db_path="data/quiz.db")
    service = QuizService(repo)
    seed_file = "data/seed_questions.json"
    if os.path.exists(seed_file):
        service.initialize_db_from_file(seed_file)
    return service


def get_viewmodel():
    service = get_quiz_service()
    return QuizViewModel(service)


try:
    vm = get_viewmodel()
    vm.ensure_state_initialized()
except Exception as e:
    logger.critical(f"🔥 System Crash: {e}", exc_info=True)
    st.error(f"System Error: {e}")
    st.stop()


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


apply_custom_styling()

# --- Sidebar ---
st.sidebar.header("Ustawienia")

if "last_ui_mode" not in st.session_state:
    st.session_state.last_ui_mode = "Codzienny Sprint (10 pytań)"
if "last_user_id" not in st.session_state:
    st.session_state.last_user_id = "Daniel"

user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"])

if user_id != st.session_state.last_user_id:
    logger.info(f"👤 UI: User changed. Resetting App.")
    st.session_state.last_user_id = user_id
    vm.reset_quiz()
    st.rerun()

ui_mode = st.sidebar.radio(
    "Tryb",
    ["Codzienny Sprint (10 pytań)", "Powtórka (Błędy)"],
    key="quiz_mode_selector"
)

if ui_mode != st.session_state.last_ui_mode:
    logger.info(f"🔀 UI: Mode changed. Resetting to IDLE.")
    st.session_state.last_ui_mode = ui_mode
    vm.reset_quiz()
    st.rerun()

MODE_MAP = {
    "Codzienny Sprint (10 pytań)": "Daily Sprint",
    "Powtórka (Błędy)": "Review (Struggling Only)"
}

if st.sidebar.button("Zeruj postęp"):
    vm.reset_quiz(user_id)
    st.sidebar.success("Postęp wyzerowany.")
    st.rerun()

# --- Debugger ---
st.sidebar.markdown("---")
with st.sidebar.expander("🕵️‍♂️ Debugger Danych"):
    if st.button("Odśwież dane"):
        st.rerun()
    repo = vm.service.repo
    stats = repo.debug_get_user_stats(user_id)
    st.write(f"**User:** {user_id}")
    st.write(f"**Total Records:** {stats['total_attempts']}")
    st.write(f"**Correct (1):** {stats['correct_count']}")
    st.write(f"**Incorrect (0):** {stats['incorrect_count']}")
    st.write("**Current FSM State:**")
    st.code(str(vm.state))


# --- UI Helpers (Refactored for OCP) ---

def render_dashboard(vm):
    """
    Renders dashboard based on the Configuration provided by the Strategy.
    No 'if mode == ...' logic here!
    """
    config = vm.dashboard_config
    profile = vm.user_profile
    if not profile: return

    # 1. Render Context Message (e.g., "3 errors remaining")
    if config.context_message:
        st.markdown(f"""
        <div style="padding: 15px; background-color: {config.context_color}; border-left: 5px solid {config.header_color}; border-radius: 5px; margin-bottom: 20px;">
            <h4 style="margin:0; color: {config.header_color};">{config.title}</h4>
            <p style="margin:0;">{config.context_message}</p>
        </div>
        """, unsafe_allow_html=True)

    # 2. Render Standard Stats if enabled
    if config.show_streak or config.show_daily_goal:
        col1, col2 = st.columns(2)
        if config.show_streak:
            col1.markdown(f'<div class="stat-box">🔥 Seria: {profile.streak_days} dni</div>', unsafe_allow_html=True)
        if config.show_daily_goal:
            col2.markdown(f'<div class="stat-box">🎯 {config.progress_text}</div>', unsafe_allow_html=True)

    # 3. Render Progress Bar
    st.progress(config.progress_value)


def render_question_header(vm, q):
    # Use the config to style the header if needed, or keep generic
    config = vm.dashboard_config
    category = getattr(q, 'category', 'Ogólne')

    # Dynamic Header based on Config Title if not using Context Message
    if not config.context_message:
        st.caption(
            f"{config.title} | Pytanie {vm.session_state.current_q_index + 1} z {len(vm.questions)} | 📂 {category}")
    else:
        st.markdown(f"**📂 Kategoria:** {category}")

    st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path)

    hint = getattr(q, 'hint', None)
    if hint:
        with st.expander("💡 Wskazówka"):
            st.info(hint)


def render_frozen_options(vm, q):
    user_selection = vm.session_state.last_selected_option
    st.markdown("### Twoja odpowiedź:")
    for key, text in q.options.items():
        prefix = "⚪"
        style_start = ""
        style_end = ""
        if key == q.correct_option:
            prefix = "✅"
            style_start = ":green[**"
            style_end = "**]"
        elif key == user_selection:
            prefix = "❌"
            style_start = ":red[**"
            style_end = "**]"
        st.markdown(f"{prefix} {style_start}{key.value}) {text}{style_end}")


# --- MAIN FSM ROUTER ---

match vm.state:

    case QuizState.IDLE:
        st.title("🎓 Warehouse Quiz")
        st.info(f"Witaj, {user_id}! Wybierz tryb i kliknij Start.")
        st.markdown(f"**Wybrany tryb:** {ui_mode}")

        if st.button("🚀 Rozpocznij Quiz", type="primary"):
            current_mode_str = MODE_MAP[ui_mode]
            vm.start_quiz(current_mode_str, user_id)
            st.rerun()

    case QuizState.LOADING:
        with st.spinner("Pobieranie pytań..."):
            pass

    case QuizState.EMPTY_STATE:
        st.warning("📭 Brak pytań w tym trybie.")
        if st.button("🔙 Wróć do Menu"):
            vm.reset_quiz()
            st.rerun()

    case QuizState.QUESTION_ACTIVE:
        render_dashboard(vm)
        q = vm.current_question

        # --- DEFENSIVE CHECK ---
        if q is None:
            logger.error(f"🚨 UI ERROR: State is ACTIVE but Question is None. Index={vm.session_state.current_q_index}")
            st.error("Wystąpił błąd ładowania pytania. Powrót do menu...")
            if st.button("Reset"):
                vm.reset_quiz()
                st.rerun()
        else:
            render_question_header(vm, q)
            st.write("")
            for key, text in q.options.items():
                st.button(
                    f"{key.value}) {text}",
                    key=f"btn_{q.id}_{key}",
                    on_click=vm.submit_answer,
                    args=(user_id, key)
                )

    case QuizState.FEEDBACK_VIEW:
        render_dashboard(vm)
        q = vm.current_question

        # --- DEFENSIVE CHECK ---
        if q is None:
             # Same error handling as above
             st.error("Błąd wyświetlania odpowiedzi.")
             if st.button("Reset"):
                vm.reset_quiz()
                st.rerun()
        else:
            render_question_header(vm, q)
            render_frozen_options(vm, q)

        # Logic for Next vs Finish button
        # We ask the service if we are effectively done (e.g. last question)
        # But for button label, we can check if it's the last index
        is_last = vm.session_state.current_q_index >= len(vm.questions) - 1
        btn_label = "Podsumowanie 🏁" if is_last else "Następne ➡️"

        st.button(btn_label, on_click=vm.next_step, type="primary")

    case QuizState.SUMMARY:
        st.balloons()
        st.title("🏁 Podsumowanie")
        st.markdown(f"### Wynik: {vm.session_state.score} / {len(vm.questions)}")

        if st.button("🔄 Wróć do Menu"):
            vm.reset_quiz()
            st.rerun()