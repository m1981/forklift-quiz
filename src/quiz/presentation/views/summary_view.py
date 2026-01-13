import streamlit as st
from src.quiz.presentation.viewmodel import QuizViewModel


def render(vm: QuizViewModel):
    st.balloons()

    # Retrieve final stats from session
    score = vm.session.score
    total = len(vm.questions)

    # Calculate percentage
    percent = (score / total * 100) if total > 0 else 0

    st.title("🏁 Podsumowanie")

    # --- Score Card ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Wynik", f"{score} / {total}")
    col2.metric("Skuteczność", f"{int(percent)}%")

    # --- Contextual Feedback ---
    if percent == 100:
        st.success("Perfekcyjnie! Mistrz magazynu! 🏆")
        col3.metric("Ocena", "⭐⭐⭐")
    elif percent >= 80:
        st.info("Bardzo dobry wynik! 👍")
        col3.metric("Ocena", "⭐⭐")
    else:
        st.warning("Warto jeszcze poćwiczyć. 📚")
        col3.metric("Ocena", "⭐")

    st.markdown("---")

    # --- Action ---
    if st.button("🔄 Wróć do Menu Głównego", type="primary", use_container_width=True):
        vm.reset()
        st.rerun()