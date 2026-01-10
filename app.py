import streamlit as st
import os
import logging
from src.models import OptionKey
from src.repository import SQLiteQuizRepository
from src.service import QuizService

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
            .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
            .question-text { font-size: 1.1rem !important; font-weight: 600; line-height: 1.4; margin-bottom: 10px; color: #31333F; }
            .stButton button { text-align: left !important; padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
            .stat-box { padding: 10px; background-color: #f0f2f6; border-radius: 5px; margin-bottom: 10px; text-align: center; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)


# --- Dependency Injection ---
@st.cache_resource
def get_service():
    repo = SQLiteQuizRepository(db_path="data/quiz.db")
    service = QuizService(repo)
    seed_file = "data/seed_questions.json"
    if os.path.exists(seed_file):
        service.initialize_db_from_file(seed_file)
    return service


try:
    service = get_service()
except Exception as e:
    st.error(f"System Error: {e}")
    st.stop()

# --- Session State ---
if 'quiz_questions' not in st.session_state: st.session_state.quiz_questions = []
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'score' not in st.session_state: st.session_state.score = 0
if 'answer_submitted' not in st.session_state: st.session_state.answer_submitted = False
if 'last_feedback' not in st.session_state: st.session_state.last_feedback = None
if 'quiz_complete' not in st.session_state: st.session_state.quiz_complete = False

apply_custom_styling()


# --- Logic Functions ---

def reset_quiz_state():
    logger.info("🔄 State Reset Triggered")
    st.session_state.quiz_questions = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None
    st.session_state.quiz_complete = False


def start_quiz(ui_mode, user_id):
    service_mode = MODE_MAPPING.get(ui_mode, "Standard")
    logger.info(f"🚀 Loading Quiz: {service_mode} for {user_id}")

    questions = service.get_quiz_questions(service_mode, user_id)
    st.session_state.quiz_questions = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None
    st.session_state.quiz_complete = False


def handle_answer(question, selected_key, user_id):
    try:
        is_correct = service.submit_answer(user_id, question, selected_key)
        if is_correct:
            st.session_state.score += 1
            feedback = {"type": "success", "msg": "✅ Dobrze!", "explanation": question.explanation}
        else:
            feedback = {"type": "error", "msg": f"❌ Źle. Poprawna: {question.correct_option.value}.",
                        "explanation": question.explanation}

        st.session_state.last_feedback = feedback
        st.session_state.answer_submitted = True

        # Check if this was the last question
        if st.session_state.current_index >= len(st.session_state.quiz_questions) - 1:
            st.session_state.quiz_complete = True

    except Exception as e:
        st.error(f"Error: {e}")


def next_question():
    st.session_state.current_index += 1
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


# --- Sidebar ---
st.sidebar.header("Ustawienia")
user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"], on_change=reset_quiz_state)
mode = st.sidebar.radio("Tryb", ["Nauka (Standard)", "Powtórka (Błędy)", "Codzienny Sprint (10 pytań)"],
                        on_change=reset_quiz_state)

if st.sidebar.button("Zeruj postęp"):
    service.repo.reset_user_progress(user_id)
    reset_quiz_state()
    st.sidebar.success("Postęp wyzerowany.")
    st.rerun()

# --- GAMIFICATION DASHBOARD ---
dashboard_placeholder = st.container()

with dashboard_placeholder:
    profile = service.get_user_profile(user_id)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="stat-box">🔥 Seria: {profile.streak_days} dni</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-box">🎯 Cel Dzienny: {profile.daily_progress}/{profile.daily_goal}</div>',
                    unsafe_allow_html=True)

    daily_pct = min(profile.daily_progress / profile.daily_goal, 1.0)
    st.progress(daily_pct)
    st.divider()

# --- Main App Flow ---

if not st.session_state.quiz_questions:
    start_quiz(mode, user_id)

questions = st.session_state.quiz_questions

if not questions:
    if "Powtórka" in mode:
        st.info("🎉 Brak błędów do poprawy!")
    elif "Sprint" in mode:
        st.balloons()
        st.success("🎉 Cel dzienny już zrealizowany!")
    else:
        st.error("Brak pytań w bazie.")

else:
    # Check if we are in the "Complete" state
    if st.session_state.quiz_complete and st.session_state.answer_submitted:
        # --- SESSION SUMMARY SCREEN ---
        fb = st.session_state.last_feedback
        if fb:
            if fb['type'] == 'success':
                st.success(fb['msg'])
            else:
                st.error(fb['msg'])
            if fb['explanation']: st.info(f"ℹ️ **Wyjaśnienie:** {fb['explanation']}")

        st.markdown("---")
        st.balloons()
        st.success(f"✨ Sesja zakończona! Wynik: {st.session_state.score}/{len(questions)}")

        if "Sprint" in mode:
            st.markdown(f"### 🚀 Postęp Dzienny: {profile.daily_progress}/{profile.daily_goal}")

        st.button("Nowy start", on_click=reset_quiz_state, type="primary")

    else:
        # --- ACTIVE QUIZ SCREEN ---
        progress = (st.session_state.current_index / len(questions))
        st.caption(f"Pytanie {st.session_state.current_index + 1} z {len(questions)}")

        q = questions[st.session_state.current_index]
        st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)

        if q.image_path and os.path.exists(q.image_path):
            # FIX: Removed width=None
            st.image(q.image_path)

        st.write("")

        if not st.session_state.answer_submitted:
            for key, text in q.options.items():
                st.button(
                    f"{key.value}) {text}",
                    key=f"btn_{q.id}_{key}",
                    on_click=handle_answer,
                    args=(q, key, user_id)
                )
        else:
            fb = st.session_state.last_feedback
            if fb:
                if fb['type'] == 'success':
                    st.success(fb['msg'])
                else:
                    st.error(fb['msg'])
                if fb['explanation']: st.info(f"ℹ️ **Wyjaśnienie:** {fb['explanation']}")

            if st.session_state.current_index < len(questions) - 1:
                st.button("Następne ➡️", on_click=next_question, type="primary")
            else:
                st.button("Podsumowanie 🏁", on_click=lambda: None, type="primary")