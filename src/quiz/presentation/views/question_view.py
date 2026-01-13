import streamlit as st
import os
from src.quiz.presentation.viewmodel import QuizViewModel


def render_active(vm: QuizViewModel):
    q = vm.current_question
    if not q:
        st.error("Internal Error: No active question found.")
        return

    # --- Header ---
    st.markdown(f"### {q.id}: {q.text}")

    # --- Image ---
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_column_width=True)

    # --- Hint ---
    if q.hint:
        with st.expander("💡 Wskazówka"):
            st.info(q.hint)

    # --- Options (Interactive) ---
    st.write("---")
    cols = st.columns(2)
    options = list(q.options.items())

    for idx, (key, text) in enumerate(options):
        # Distribute buttons across 2 columns
        col = cols[idx % 2]
        if col.button(f"{key.value}) {text}", key=f"btn_{q.id}_{key}", use_container_width=True):
            vm.submit_answer(key)
            st.rerun()


def render_feedback(vm: QuizViewModel):
    q = vm.current_question
    if not q: return

    # --- Header (Same as active) ---
    st.markdown(f"### {q.id}: {q.text}")
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, width=300)

    # --- Feedback Area ---
    last_correct = vm.state.get('last_correct', False)
    last_selected = vm.state.get('last_selected')

    if last_correct:
        st.success("✅ Dobra odpowiedź!")
    else:
        st.error(f"❌ Źle. Wybrano: {last_selected.value if last_selected else '?'}")
        st.info(f"Poprawna odpowiedź to: **{q.correct_option.value}) {q.options[q.correct_option]}**")

        if q.explanation:
            st.markdown(f"> **Wyjaśnienie:** {q.explanation}")

    # --- Frozen Options (Visual Only) ---
    st.write("---")
    for key, text in q.options.items():
        prefix = "⚪"
        if key == q.correct_option:
            prefix = "✅"
        elif key == last_selected and not last_correct:
            prefix = "❌"

        st.markdown(f"**{prefix} {key.value})** {text}")

    # --- Navigation ---
    st.write("")
    st.write("")

    # Check if this is the last question to change button text
    # Note: We ask the VM/Service logic implicitly via list length,
    # but strictly speaking, the VM should expose 'is_last_question' property for cleaner UI logic.
    # For now, we use a generic "Next" which handles both Next Question and Finish.

    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        vm.next_step()
        st.rerun()