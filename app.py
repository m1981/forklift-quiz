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

# 🔇 Silence Noise
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
user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"])

# Initialize last_ui_mode if missing
if "last_ui_mode" not in st.session_state:
    st.session_state.last_ui_mode = "Codzienny Sprint (10 pytań)"

# Sidebar Radio
ui_mode = st.sidebar.radio(
    "Tryb",
    ["Codzienny Sprint (10 pytań)", "Powtórka (Błędy)"],
    key="quiz_mode_selector"
)

# 3. Reactive Logic: If mode changed, reset FSM to IDLE
if ui_mode != st.session_state.last_ui_mode:
    logger.info(f"🔀 UI: Mode changed from '{st.session_state.last_ui_mode}' to '{ui_mode}'. Resetting to IDLE.")
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

# --- NEW: DEBUG SECTION IN SIDEBAR ---
st.sidebar.markdown("---")
with st.sidebar.expander("🕵️‍♂️ Debugger Danych"):
    if st.button("Odśwież dane"):
        st.rerun()

    # Fetch raw stats directly from repo
    repo = vm.service.repo
    stats = repo.debug_get_user_stats(user_id)

    st.write(f"**User:** {user_id}")
    st.write(f"**Total Records:** {stats['total_attempts']}")
    st.write(f"**Correct (1):** {stats['correct_count']}")
    st.write(f"**Incorrect (0):** {stats['incorrect_count']}")
    st.write("**Incorrect IDs:**")
    st.code(str(stats['incorrect_ids']))

    st.write("**Current FSM State:**")
    st.code(str(vm.state))

    st.write("**Session Questions:**")
    st.write(len(vm.questions))

# -------------------------------------

# --- UI Helpers ---
def render_dashboard(vm, user_id, ui_mode):
    """
    Renders different dashboards based on the mode.
    """
    profile = vm.user_profile
    if not profile: return

    # 🔴 REVIEW MODE DASHBOARD (Distinct Style)
    if "Powtórka" in ui_mode:
        # Calculate progress within this specific error set
        total_errors = len(vm.questions)
        current_q_num = st.session_state.current_index + 1
        remaining = total_errors - st.session_state.current_index

        st.markdown(f"""
        <div style="padding: 15px; background-color: #fff0f0; border-left: 5px solid #ff4b4b; border-radius: 5px; margin-bottom: 20px;">
            <h4 style="margin:0; color: #ff4b4b;">🛠️ Tryb Poprawy Błędów</h4>
            <p style="margin:0;">Pozostało do naprawienia: <strong>{remaining}</strong> (z {total_errors})</p>
        </div>
        """, unsafe_allow_html=True)
        if total_errors > 0:
            st.progress(st.session_state.current_index / total_errors)
    else:
        col1, col2 = st.columns(2)
        col1.markdown(f'<div class="stat-box">🔥 Seria: {profile.streak_days} dni</div>', unsafe_allow_html=True)
        col2.markdown(f'<div class="stat-box">🎯 Cel: {profile.daily_progress}/{profile.daily_goal}</div>',
                      unsafe_allow_html=True)
        st.progress(min(profile.daily_progress / profile.daily_goal, 1.0))


def render_question_header(vm, q, ui_mode):
    category = getattr(q, 'category', 'Ogólne')

    # 🔴 REVIEW HEADER
    if "Powtórka" in ui_mode:
        # No standard caption, use a distinct label
        st.markdown(f"**📂 Kategoria:** {category}")

    # 🔵 SPRINT HEADER
    else:
        st.caption(f"Pytanie {st.session_state.current_index + 1} z {len(vm.questions)} | 📂 {category}")

    # Question Text
    st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path)

    hint = getattr(q, 'hint', None)
    if hint:
        with st.expander("💡 Wskazówka"):
            st.info(hint)

def render_frozen_options(vm, q):
    user_selection = st.session_state.get('last_selected_option')
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

logger.debug(f"🚦 ROUTER: Matching State '{vm.state}'")

match vm.state:

    case QuizState.IDLE:
        st.title("🎓 Warehouse Quiz")

        # --- DEBUG INFO ON SCREEN ---
        st.warning(f"DEBUG: App is IDLE. Mode: {ui_mode}")
        if "Powtórka" in ui_mode:
             repo = vm.service.repo
             errs = repo.get_incorrect_question_ids(user_id)
             if not errs:
                 st.success("🎉 Brak błędów do poprawy! Przełącz na Sprint.")
             else:
                 st.warning(f"⚠️ Masz {len(errs)} błędów do poprawy.")
        # ----------------------------

        st.info(f"Witaj, {user_id}! Wybierz tryb i kliknij Start.")
        st.markdown(f"**Wybrany tryb:** {ui_mode}")

        if st.button("🚀 Rozpocznij Quiz", type="primary"):
            # CRITICAL: Use the current ui_mode from the widget, not a cached variable
            current_mode_str = MODE_MAP[ui_mode]
            logger.info(f"🚀 UI: User clicked Start. Mode='{ui_mode}' -> '{current_mode_str}'")
            vm.start_quiz(current_mode_str, user_id)
            st.rerun()

    case QuizState.LOADING:
        with st.spinner("Pobieranie pytań..."):
            pass

    case QuizState.EMPTY_STATE:
        st.warning("📭 Brak pytań w tym trybie.")
        if "Powtórka" in ui_mode:
            st.success("🎉 Brak błędów do poprawy!")

        if st.button("🔙 Wróć do Menu"):
            vm.reset_quiz()
            st.rerun()

    case QuizState.QUESTION_ACTIVE:
        # Pass ui_mode here
        render_dashboard(vm, user_id, ui_mode)
        q = vm.current_question
        render_question_header(vm, q, ui_mode)

        st.write("")
        for key, text in q.options.items():
            st.button(
                f"{key.value}) {text}",
                key=f"btn_{q.id}_{key}",
                on_click=vm.submit_answer,
                args=(user_id, key)
            )

    case QuizState.FEEDBACK_VIEW:
        # Pass ui_mode here
        render_dashboard(vm, user_id, ui_mode)
        q = vm.current_question
        render_question_header(vm, q, ui_mode)
        render_frozen_options(vm, q)

        st.divider()
        fb = st.session_state.last_feedback
        if fb:
            if fb['type'] == 'success':
                st.success(fb['msg'])
            else:
                st.error(fb['msg'])
                if fb.get('explanation'):
                    st.info(f"ℹ️ {fb['explanation']}")

        # Logic for Next vs Finish button
        is_last = st.session_state.current_index >= len(vm.questions) - 1
        btn_label = "Podsumowanie 🏁" if is_last else "Następne ➡️"

        st.button(btn_label, on_click=vm.next_step, type="primary")

    case QuizState.SUMMARY:
        st.balloons()
        st.title("🏁 Podsumowanie")
        st.markdown(f"### Wynik: {st.session_state.score} / {len(vm.questions)}")

        if "Powtórka" in ui_mode:
            remaining = len(vm.service.repo.get_incorrect_question_ids(user_id))
            if remaining > 0:
                st.warning(f"⚠️ Pozostało {remaining} błędów.")
            else:
                st.success("🎉 Wszystkie błędy poprawione!")

        if st.button("🔄 Wróć do Menu"):
            vm.reset_quiz()
            st.rerun()