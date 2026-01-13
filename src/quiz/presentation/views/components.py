import streamlit as st
from src.quiz.application.strategies import DashboardConfig


def apply_styles():
    st.markdown("""
        <style>
            .block-container { padding-top: 2rem !important; }
            .stat-box { padding: 10px; background-color: #f0f2f6; border-radius: 5px; text-align: center; font-weight: bold; }
            .question-text { font-size: 1.2rem; font-weight: 600; margin-bottom: 1rem; }
        </style>
    """, unsafe_allow_html=True)


def render_sidebar(current_user: str, current_mode: str) -> tuple[str, str, bool]:
    st.sidebar.header("⚙️ Ustawienia")

    user_id = st.sidebar.selectbox("Użytkownik", ["Daniel", "Michał"], index=0 if current_user == "Daniel" else 1)
    mode = st.sidebar.radio("Tryb", ["Daily Sprint", "Review (Struggling Only)"],
                            index=0 if "Sprint" in current_mode else 1)

    reset = st.sidebar.button("Zeruj postęp")

    # Debug Info
    with st.sidebar.expander("🕵️‍♂️ Telemetry"):
        st.caption("Trace ID: " + str(st.session_state.get('correlation_id', 'N/A')))

    return user_id, mode, reset


def render_dashboard(config: DashboardConfig):
    if config.context_message:
        st.info(config.context_message, icon="ℹ️")

    col1, col2 = st.columns(2)
    if config.show_streak:
        col1.markdown(f'<div class="stat-box">🔥 {config.title}</div>', unsafe_allow_html=True)
    if config.show_daily_goal:
        col2.markdown(f'<div class="stat-box">🎯 {config.progress_text}</div>', unsafe_allow_html=True)

    st.progress(config.progress_value)