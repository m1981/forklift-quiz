import streamlit as st
import os


def render_active(payload, callback):
    """
    :param payload: QuestionStepPayload
    :param callback: function(action, payload)
    """
    q = payload.question

    # --- Header ---
    st.markdown(f"### Pytanie {payload.current_index}/{payload.total_count}")
    st.markdown(f"**{q.text}**")

    # --- Image ---
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_column_width=True)

    # --- Hint ---
    if q.hint:
        with st.expander("💡 Wskazówka"):
            st.info(q.hint)

    # --- Options ---
    st.write("---")
    cols = st.columns(2)
    options = list(q.options.items())

    for idx, (key, text) in enumerate(options):
        col = cols[idx % 2]
        # We use the callback to send the action "SUBMIT_ANSWER" with the selected key
        if col.button(f"{key.value}) {text}", key=f"btn_{q.id}_{key}", use_container_width=True):
            callback("SUBMIT_ANSWER", key)


def render_feedback(payload, callback):
    """
    :param payload: QuestionStepPayload (with last_feedback populated)
    """
    q = payload.question
    fb = payload.last_feedback

    st.markdown(f"### Pytanie {payload.current_index}/{payload.total_count}")
    st.markdown(f"**{q.text}**")

    if fb['is_correct']:
        st.success("✅ Dobra odpowiedź!")
    else:
        st.error(f"❌ Źle. Wybrano: {fb['selected'].value}")
        st.info(f"Poprawna odpowiedź to: **{fb['correct_option'].value}) {q.options[fb['correct_option']]}**")
        if fb.get('explanation'):
            st.markdown(f"> **Wyjaśnienie:** {fb['explanation']}")

    st.write("---")
    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        callback("NEXT_QUESTION", None)