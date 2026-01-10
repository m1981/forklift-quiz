import streamlit as st
import os
import logging
from src.models import OptionKey
from src.repository import SQLiteQuizRepository
from src.service import QuizService

# --- 1. Logging Configuration (Visualizing the Sequence) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
st.set_page_config(page_title="Warehouse Certification Quiz", layout="centered")

# --- Constants: Translation Layer ---
# Maps Polish UI labels to the English logic required by Service.py
MODE_MAPPING = {
    "Nauka": "Standard",
    "Powtórka": "Review (Struggling Only)"
}


# --- Custom CSS ---
def apply_custom_styling():
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
            .question-text { font-size: 1.1rem !important; font-weight: 600; line-height: 1.4; margin-bottom: 10px; color: #31333F; }
            .stButton button { text-align: left !important; padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
            div[data-testid="stVerticalBlock"] > div { gap: 0.5rem !important; }
        </style>
    """, unsafe_allow_html=True)


# --- Dependency Injection ---
@st.cache_resource
def get_service():
    logger.info("🔌 Initializing Service and Repository...")
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

# --- Session State Initialization ---
if 'quiz_questions' not in st.session_state: st.session_state.quiz_questions = []
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'score' not in st.session_state: st.session_state.score = 0
if 'answer_submitted' not in st.session_state: st.session_state.answer_submitted = False
if 'last_feedback' not in st.session_state: st.session_state.last_feedback = None

apply_custom_styling()


# --- Logic Functions ---

def reset_quiz_state():
    """
    Callback: Clears the current questions.
    """
    logger.info("🔄 CALLBACK TRIGGERED: reset_quiz_state. Wiping session data.")
    st.session_state.quiz_questions = []
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


def start_quiz(ui_mode, user_id):
    """Fetches data and populates state"""
    # Translate Polish UI mode to English Service Mode
    service_mode = MODE_MAPPING.get(ui_mode, "Standard")

    logger.info(f"🚀 STARTING QUIZ LOAD | User: {user_id} | UI Mode: {ui_mode} -> Service Mode: {service_mode}")

    questions = service.get_quiz_questions(service_mode, user_id)

    logger.info(f"📦 DB RETURNED: {len(questions)} questions for this mode.")

    st.session_state.quiz_questions = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


def handle_answer(question, selected_key, user_id):
    try:
        logger.info(f"📝 User {user_id} answered Q{question.id}: {selected_key.value}")
        is_correct = service.submit_answer(user_id, question, selected_key)

        if is_correct:
            st.session_state.score += 1
            feedback = {"type": "success", "msg": "✅ Dobrze!", "explanation": question.explanation}
            logger.info("   -> Result: CORRECT")
        else:
            feedback = {"type": "error", "msg": f"❌ Źle. Poprawna: {question.correct_option.value}.",
                        "explanation": question.explanation}
            logger.info("   -> Result: INCORRECT")

        st.session_state.last_feedback = feedback
        st.session_state.answer_submitted = True
    except Exception as e:
        logger.error(f"Error saving answer: {e}")
        st.error(f"Error saving answer: {e}")


def next_question():
    logger.info("➡️ User clicked Next Question")
    st.session_state.current_index += 1
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


# --- Sidebar ---
st.sidebar.header("Ustawienia")

user_id = st.sidebar.selectbox(
    "Użytkownik",
    ["Daniel", "Michał"],
    on_change=reset_quiz_state
)

# UI uses Polish labels
mode = st.sidebar.radio(
    "Tryb",
    ["Nauka", "Powtórka"],
    on_change=reset_quiz_state
)

if st.sidebar.button("Zeruj postęp"):
    logger.warning(f"🗑️ RESETTING PROGRESS for {user_id}")
    service.repo.reset_user_progress(user_id)
    reset_quiz_state()
    st.sidebar.success(f"Postęp wyzerowany dla: {user_id}")
    st.rerun()

# --- Main App Flow ---

# 1. Auto-Start if empty
if not st.session_state.quiz_questions:
    logger.info("⚡ Session empty. Calling start_quiz()...")
    start_quiz(mode, user_id)

questions = st.session_state.quiz_questions

st.caption("🏗️ Warehouse Certification Quiz")

# 2. Handle Empty State
if not questions:
    # Check against the Polish label "Powtórka"
    if mode == "Powtórka":
        logger.info("🎉 Review mode empty - User has no incorrect answers.")
        st.info("🎉 Świetna robota! Nie masz żadnych pytań do powtórki.")
        st.markdown("Wróć do trybu **Nauka**, aby kontynuować.")
    else:
        logger.error("❌ Standard mode empty - Check seed file.")
        st.error("Brak pytań w bazie danych. Sprawdź plik 'data/seed_questions.json'.")

# 3. Quiz Interface
else:
    # Progress
    progress = (st.session_state.current_index / len(questions))
    st.progress(progress)
    st.caption(f"Pytanie {st.session_state.current_index + 1} z {len(questions)}")

    q = questions[st.session_state.current_index]

    # Question Text
    st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)

    # Image
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    st.write("")

    # Interaction
    if not st.session_state.answer_submitted:
        st.write("Wybierz odpowiedź:")
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
            st.balloons()
            st.success(f"Koniec! Wynik sesji: {st.session_state.score}/{len(questions)}")
            st.button("Nowy start", on_click=reset_quiz_state, type="primary")