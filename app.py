import streamlit as st
import os
from src.models import OptionKey
from src.repository import SQLiteQuizRepository
from src.service import QuizService

# --- Configuration ---
st.set_page_config(page_title="Warehouse Certification Quiz", layout="centered")


# --- Custom CSS (Mobile Optimization) ---
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
    # Sequence 1: Startup
    repo = SQLiteQuizRepository(db_path="data/quiz.db")
    service = QuizService(repo)

    seed_file = "data/seed_questions.json"
    if os.path.exists(seed_file):
        service.initialize_db_from_file(seed_file)
    return service


try:
    service = get_service()
except Exception as e:
    st.error(f"Critical System Error: Could not initialize application. {e}")
    st.stop()

# --- Session State ---
if 'current_index' not in st.session_state: st.session_state.current_index = 0
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_questions' not in st.session_state: st.session_state.quiz_questions = []
if 'answer_submitted' not in st.session_state: st.session_state.answer_submitted = False
if 'last_feedback' not in st.session_state: st.session_state.last_feedback = None

apply_custom_styling()

# --- Sidebar ---
st.sidebar.header("Settings")
user_id = st.sidebar.selectbox("Select User", ["User A", "User B"])
mode = st.sidebar.radio("Quiz Mode", ["Standard", "Review (Struggling Only)"])

if st.sidebar.button("Reset My Progress"):
    service.repo.reset_user_progress(user_id)
    st.sidebar.success(f"Progress reset for {user_id}")
    st.rerun()


# --- Logic ---
def start_quiz():
    # Sequence 2 & 3: Fetching
    questions = service.get_quiz_questions(mode, user_id)
    st.session_state.quiz_questions = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


def handle_answer(question, selected_key):
    # Sequence 2: Submit & Save
    try:
        is_correct = service.submit_answer(user_id, question, selected_key)

        if is_correct:
            st.session_state.score += 1
            feedback = {"type": "success", "msg": "✅ Correct!", "explanation": question.explanation}
        else:
            feedback = {"type": "error", "msg": f"❌ Incorrect. The correct answer was {question.correct_option.value}.",
                        "explanation": question.explanation}

        st.session_state.last_feedback = feedback
        st.session_state.answer_submitted = True
    except Exception as e:
        st.error(f"Error saving answer: {e}")


def next_question():
    st.session_state.current_index += 1
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


# --- Main Flow ---
if not st.session_state.quiz_questions:
    start_quiz()

questions = st.session_state.quiz_questions

st.caption("🏗️ Warehouse Certification Quiz")

if not questions:
    if mode == "Review (Struggling Only)":
        st.info("Great job! You have no struggling questions to review.")
    else:
        st.error("No questions found. Please check 'data/seed_questions.json'.")
else:
    # Progress
    progress = (st.session_state.current_index / len(questions))
    st.progress(progress)
    st.caption(f"Question {st.session_state.current_index + 1} of {len(questions)}")

    q = questions[st.session_state.current_index]

    # Question Text
    st.markdown(f'<div class="question-text">{q.id}: {q.text}</div>', unsafe_allow_html=True)

    # Image
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    st.write("")

    # Interaction
    if not st.session_state.answer_submitted:
        st.write("Select an answer:")
        for key, text in q.options.items():
            st.button(
                f"{key.value}) {text}",
                key=f"btn_{q.id}_{key}",
                # Removed use_container_width to prevent warnings, relying on CSS for width
                on_click=handle_answer,
                args=(q, key)
            )
    else:
        fb = st.session_state.last_feedback
        if fb:
            if fb['type'] == 'success':
                st.success(fb['msg'])
            else:
                st.error(fb['msg'])
            if fb['explanation']: st.info(f"ℹ️ **Explanation:** {fb['explanation']}")

        if st.session_state.current_index < len(questions) - 1:
            st.button("Next Question ➡️", on_click=next_question, type="primary")
        else:
            st.balloons()
            st.success(f"Quiz Complete! Final Score: {st.session_state.score}/{len(questions)}")
            st.button("Start New Quiz", on_click=start_quiz, type="primary")