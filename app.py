import streamlit as st
import os
import logging
from src.repository import SQLiteQuizRepository
from src.service import QuizService
from src.viewmodel import QuizViewModel  # <--- NEW IMPORT

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
    st.error(f"System Error: {e}")
    st.stop()

apply_custom_styling()

# --- Sidebar ---
st.sidebar.header("Ustawienia")


# We use a callback to force a reload when settings change
def on_settings_change():
    # Just clear the questions to force a reload in the main flow
    st.session_state.quiz_questions = []


user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"], on_change=on_settings_change)
ui_mode = st.sidebar.radio("Tryb", list(MODE_MAPPING.keys()), on_change=on_settings_change)

if st.sidebar.button("Zeruj postęp"):
    vm.reset_progress(user_id)
    st.sidebar.success("Postęp wyzerowany.")
    st.rerun()

# --- Main Flow ---

# 1. Auto-Load if empty
if not vm.questions:
    service_mode = MODE_MAPPING.get(ui_mode, "Standard")
    vm.load_quiz(service_mode, user_id)

# 2. Dashboard (Always Visible & Synced)
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

# 3. Content Area
if not vm.questions:
    if "Powtórka" in ui_mode:
        st.info("🎉 Brak błędów do poprawy!")
    elif "Sprint" in ui_mode:
        st.balloons()
        st.success("🎉 Cel dzienny już zrealizowany!")
    else:
        st.error("Brak pytań w bazie.")

elif vm.is_complete and st.session_state.answer_submitted:
    # --- SUMMARY SCREEN ---
    # Show feedback for the very last question first
    fb = st.session_state.last_feedback
    if fb:
        if fb['type'] == 'success':
            st.success(fb['msg'])
        else:
            st.error(fb['msg'])
        if fb['explanation']: st.info(f"ℹ️ **Wyjaśnienie:** {fb['explanation']}")

    st.markdown("---")
    st.balloons()
    st.success(f"✨ Sesja zakończona! Wynik: {st.session_state.score}/{len(vm.questions)}")
    st.button("Nowy start", on_click=on_settings_change, type="primary")

else:
    # --- QUIZ SCREEN ---
    q = vm.current_question

    # Progress Text
    st.caption(f"Pytanie {st.session_state.current_index + 1} z {len(vm.questions)}")

    # Question
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
                on_click=vm.submit_answer,  # <--- Delegating to ViewModel
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
            # Trigger Summary
            st.button("Podsumowanie 🏁", on_click=lambda: None, type="primary")