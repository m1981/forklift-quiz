import streamlit as st
import os
from src.models import OptionKey
from src.repository import SQLiteQuizRepository
from src.service import QuizService

# --- Configuration ---
st.set_page_config(page_title="Wozki", layout="centered")


# --- Dependency Injection ---
@st.cache_resource
def get_service():
    repo = SQLiteQuizRepository(db_path="data/quiz.db")
    service = QuizService(repo)
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
if 'answer_submitted' not in st.session_state:
    st.session_state.answer_submitted = False
if 'last_feedback' not in st.session_state:
    st.session_state.last_feedback = None

# --- Sidebar ---
st.sidebar.header("Settings")
user_id = st.sidebar.selectbox("Select User", ["User A", "User B"])
mode = st.sidebar.radio("Quiz Mode", ["Standard", "Review (Struggling Only)"])

if st.sidebar.button("Reset My Progress"):
    service.repo.reset_user_progress(user_id)
    st.sidebar.success(f"Progress reset for {user_id}")
    st.rerun()


# --- Logic Functions ---
def start_quiz():
    questions = service.get_quiz_questions(mode, user_id)
    st.session_state.quiz_questions = questions
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


def handle_answer(question, selected_key):
    """Callback function triggered immediately when an answer button is clicked"""
    is_correct = service.submit_answer(user_id, question, selected_key)

    if is_correct:
        st.session_state.score += 1
        feedback = {
            "type": "success",
            "msg": "✅ Correct!",
            "explanation": question.explanation
        }
    else:
        feedback = {
            "type": "error",
            "msg": f"❌ Incorrect. The correct answer was {question.correct_option.value}.",
            "explanation": question.explanation
        }

    st.session_state.last_feedback = feedback
    st.session_state.answer_submitted = True


def next_question():
    """Callback to move to next question"""
    st.session_state.current_index += 1
    st.session_state.answer_submitted = False
    st.session_state.last_feedback = None


# --- Main App Flow ---

# 1. Load Questions if needed
if not st.session_state.quiz_questions:
    start_quiz()

questions = st.session_state.quiz_questions


# 2. Handle Empty State
if not questions:
    if mode == "Review (Struggling Only)":
        st.info("Great job! You have no struggling questions to review.")
    else:
        st.error("No questions found in database.")

# 3. Quiz Interface
else:
    # Progress Bar
    progress = (st.session_state.current_index / len(questions))
    st.progress(progress)
    st.caption(f"Pytanie {st.session_state.current_index + 1} of {len(questions)}")

    # Get Current Question
    q = questions[st.session_state.current_index]

    # Display Question Text
    st.subheader(f"{q.id}: {q.text}")

    # Display Image
    if q.image_path and os.path.exists(q.image_path):
        # Updated: use_container_width=True -> width="stretch" (or just rely on default behavior for images)
        # Note: st.image doesn't strictly use width='stretch' in the same way as buttons yet in all versions,
        # but use_container_width is the specific deprecation target.
        # For st.image, use_column_width is the old param, use_container_width is the current one.
        # If your specific version asks for width='stretch' on buttons, apply it there.
        st.image(q.image_path, use_container_width=True)

    # 4. State Machine: Input vs Feedback

    if not st.session_state.answer_submitted:
        # STATE A: Waiting for Input
        st.write("Wybierz odpowiedź:")

        # Loop through options and create a button for each
        for key, text in q.options.items():
            # We use a callback (on_click) to handle the logic immediately
            st.button(
                f"{key.value}) {text}",
                key=f"btn_{q.id}_{key}",
                # If your specific Streamlit version demands width='stretch' for buttons specifically:
                # type="secondary",
                on_click=handle_answer,
                args=(q, key)
            )

    else:
        # STATE B: Feedback Shown (Answer buttons hidden)
        fb = st.session_state.last_feedback

        if fb['type'] == 'success':
            st.success(fb['msg'])
        else:
            st.error(fb['msg'])

        if fb['explanation']:
            st.info(f"ℹ️ **Explanation:** {fb['explanation']}")

        # Next Button Logic
        if st.session_state.current_index < len(questions) - 1:
            st.button("Next Question ➡️", on_click=next_question, type="primary", use_container_width=True)
        else:
            st.balloons()
            st.success(f"Quiz Complete! Final Score: {st.session_state.score}/{len(questions)}")
            st.button("Start New Quiz", on_click=start_quiz, type="primary")