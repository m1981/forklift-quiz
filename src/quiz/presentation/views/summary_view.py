from typing import Any

import streamlit as st

from src.config import GameConfig


def render_summary_screen(service: Any, user_id: str) -> None:
    # Ensure all profile changes are saved before showing summary
    service.profile_manager.flush_on_exit()

    # 1. Get State
    score = st.session_state.get("score", 0)
    total = len(st.session_state.get("quiz_questions", []))
    errors = st.session_state.get("quiz_errors", [])

    is_passed = score >= GameConfig.PASSING_SCORE

    # 2. Render UI
    if is_passed:
        st.balloons()

    st.title("🏁 Podsumowanie")

    col1, col2, col3 = st.columns(3)
    col1.metric("Wynik", f"{score} / {total}")

    percent = (score / total * 100) if total > 0 else 0
    col2.metric("Skuteczność", f"{int(percent)}%")

    if is_passed:
        st.success("Zaliczone! Gratulacje! 🏆")
        col3.metric("Ocena", "POZYTYWNA")
    else:
        st.error(f"Niezaliczone. Wymagane: {GameConfig.PASSING_SCORE} pkt.")
        col3.metric("Ocena", "NEGATYWNA")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    # 3. Actions
    with col_a:
        if st.button("🔄 Menu Główne", type="secondary", use_container_width=True):
            st.session_state.screen = "dashboard"
            st.rerun()

    with col_b:
        # Only show Review button if there were errors
        if errors:
            if st.button("🛠️ Popraw Błędy", type="primary", use_container_width=True):
                # Logic to restart quiz with errors
                questions = service.repo.get_questions_by_ids(errors)
                service._reset_quiz_state(questions, "🛠️ Poprawa Błędów")
                st.rerun()
