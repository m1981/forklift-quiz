import streamlit as st

def render(payload, callback):
    """
    :param payload: SummaryPayload
    """
    st.balloons()

    score = payload.score
    total = payload.total
    percent = (score / total * 100) if total > 0 else 0

    st.title("🏁 Podsumowanie")

    col1, col2, col3 = st.columns(3)
    col1.metric("Wynik", f"{score} / {total}")
    col2.metric("Skuteczność", f"{int(percent)}%")

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

    # --- NEW BUTTON LOGIC ---
    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🔄 Menu Główne", type="secondary", use_container_width=True):
            callback("FINISH", None)

    with col_b:
        # Only show Review button if there were errors
        if payload.has_errors:
            if st.button("🛠️ Popraw Błędy", type="primary", use_container_width=True):
                callback("REVIEW_MISTAKES", None)