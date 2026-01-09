import streamlit as st
import os
from src.models import OptionKey
from src.repository import SQLiteQuizRepository
from src.service import QuizService

# --- Configuration ---
st.set_page_config(page_title="Warehouse Certification Quiz", layout="centered")


# --- Dependency Injection ---
# We cache the service to avoid reloading DB connections on every rerun
@st.cache_resource
def get_service():
    repo = SQLiteQuizRepository(db_path="data/quiz.db")
    service = QuizService(repo)
    # Seed DB if needed
    if os.path.exists("data/seed_questions.json"):
        service.initialize_db_from_file("data/seed_questions.json")
    return service


service = get_service()

# --- Session State Initialization ---
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'quiz_questions' not in st.session_state:
    st.session_state.quiz_questions = []
if 'last_feedback' not in st.session_state:
    st.session_state.last_feedback = None

# --- Sidebar: User & Mode Selection ---
st.sidebar.header("Settings")
user_id = st.sidebar.selectbox("Select User", ["User A", "User B"])
mode = st.sidebar.radio("Quiz Mode", ["Standard", "Review (Struggling Only)"])

if st.sidebar.button("Reset My Progress"):
    service.repo.reset_user_progress(user_id)
    st.sidebar.success(f"Progress reset for {user_id}")
    st.rerun()


# --- Main Logic ---
def start_quiz():
    # Load questions based on mode
    questions = service.get_quiz_questions(mode, user_id)
    st.session_state.quiz_questions = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.last_feedback = None


# If questions aren't loaded or mode changed, (re)start
if not st.session_state.quiz_questions:
    start_quiz()

# --- UI Rendering ---
st.title("🏗️ Warehouse Quiz App")

questions = st.session_state.quiz_questions

if not questions:
    if mode == "Review (Struggling Only)":
        st.info("Great job! You have no struggling questions to review.")
    else:
        st.error("No questions found in database.")
else:
    # Progress Bar
    progress = (st.session_state.current_index / len(questions))
    st.progress(progress)
    st.caption(f"Question {st.session_state.current_index + 1} of {len(questions)}")

    # Get Current Question
    q = questions[st.session_state.current_index]

    # Display Question
    st.subheader(f"Q{q.id}: {q.text}")

    # Display Image if exists
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)
    elif q.image_path:
        st.warning(f"Image not found: {q.image_path}")

    # Answer Form
    with st.form(key=f"form_{q.id}"):
        # Create radio options
        options_display = {k: f"{k.value}) {v}" for k, v in q.options.items()}
        selection = st.radio("Choose answer:", list(options_display.keys()), format_func=lambda x: options_display[x])

        submit_btn = st.form_submit_button("Submit Answer")

        if submit_btn:
            is_correct = service.submit_answer(user_id, q, selection)

            if is_correct:
                st.session_state.score += 1
                feedback = {
                    "type": "success",
                    "msg": "✅ Correct!",
                    "explanation": q.explanation
                }
            else:
                feedback = {
                    "type": "error",
                    "msg": f"❌ Incorrect. The correct answer was {q.correct_option.value}.",
                    "explanation": q.explanation
                }

            st.session_state.last_feedback = feedback

    # Feedback Display (Outside form to persist)
    if st.session_state.last_feedback:
        fb = st.session_state.last_feedback
        if fb['type'] == 'success':
            st.success(fb['msg'])
        else:
            st.error(fb['msg'])

        if fb['explanation']:
            st.info(f"ℹ️ **Explanation:** {fb['explanation']}")

        # Next Button
        if st.button("Next Question ➡️"):
            if st.session_state.current_index < len(questions) - 1:
                st.session_state.current_index += 1
                st.session_state.last_feedback = None
                st.rerun()
            else:
                st.balloons()
                st.success(f"Quiz Complete! Score: {st.session_state.score}/{len(questions)}")
                if st.button("Restart"):
                    start_quiz()
                    st.rerun()