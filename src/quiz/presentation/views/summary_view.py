import streamlit as st
from src.config import GameConfig

def render(payload, callback):
    score = payload.score
    total = payload.total

    # <--- NEW: Check Passing Score
    is_passed = score >= GameConfig.PASSING_SCORE

    if is_passed:
        st.balloons() # Only show balloons if passed

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
    with col_a:
        if st.button("🔄 Menu Główne", type="secondary", use_container_width=True):
            callback("FINISH", None)

    with col_b:
        # Only show Review button if there were errors
        if payload.has_errors:
            if st.button("🛠️ Popraw Błędy", type="primary", use_container_width=True):
                callback("REVIEW_MISTAKES", None)