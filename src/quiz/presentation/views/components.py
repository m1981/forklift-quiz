import streamlit as st

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

    # Note: The mode selection here is just for the UI state.
    # The actual flow start happens via the buttons in app.py
    mode = st.sidebar.radio("Tryb", ["Daily Sprint", "Review (Struggling Only)"],
                            index=0 if "Sprint" in current_mode else 1)

    reset = st.sidebar.button("Zeruj postęp")

    # Debug Info
    with st.sidebar.expander("🕵️‍♂️ Telemetry"):
        st.caption("Trace ID: " + str(st.session_state.get('correlation_id', 'N/A')))

    return user_id, mode, reset

# DELETED: render_dashboard (It relied on the obsolete DashboardConfig)