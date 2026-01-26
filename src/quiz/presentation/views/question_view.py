import os
from collections.abc import Callable
from typing import Any

import streamlit as st

# Import the new component
from src.components.mobile_suite import mobile_header, mobile_option, mobile_result_row


def _render_compact_header(payload: Any, callback: Callable[[str, Any], None]) -> None:
    # ... (Same as before) ...
    cat_name = payload.category_name
    if len(cat_name) > 40:
        cat_name = cat_name[:40] + "..."

    context_text = f"{payload.current_index}/{payload.total_count} • {cat_name}"

    if mobile_header(
        context=context_text, progress=payload.category_mastery, key="mob_header"
    ):
        callback("NAVIGATE_HOME", None)


def render_active(payload: Any, callback: Callable[[str, Any], None]) -> None:
    # ... (Same as before) ...
    _render_compact_header(payload, callback)

    q = payload.question

    st.markdown(
        f"""
        <div style="
            font-size: 1rem;
            font-weight: 400;
            color: #31333F;
            margin-top: 10px;
            margin-bottom: 15px;
            line-height: 1.4;">
            {q.text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    for key, text in q.options.items():
        clicked_key = mobile_option(key.value, text, key=f"opt_{q.id}_{key}")
        if clicked_key:
            callback("SUBMIT_ANSWER", key)

    if q.hint:
        with st.expander("💡 Wskazówka"):
            st.info(q.hint)


def render_feedback(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """
    Renders the feedback screen using the new Gentle Result Rows.
    """
    # 1. Header
    _render_compact_header(payload, callback)

    q = payload.question
    fb = payload.last_feedback

    # 2. Question Text
    st.markdown(f"**{q.text}**")

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # 3. Status Message (Optional - The cards explain themselves now)
    # We can keep a very small text or remove it entirely to save space.
    # Let's keep it minimal.
    if fb["is_correct"]:
        st.markdown(":green[**Dobrze!**]")
    else:
        st.markdown(":red[**Niestety źle.**]")

    # 4. Result Rows (The Elegant Part)
    for key, text in q.options.items():
        state = "neutral"

        # Logic to determine color
        if key == fb["correct_option"]:
            if key == fb["selected"]:
                state = "correct"  # You picked right
            else:
                state = "missed"  # You picked wrong, but this was the right one
        elif key == fb["selected"] and not fb["is_correct"]:
            state = "wrong"  # You picked this and it was wrong

        # Render the V2 Component
        mobile_result_row(key.value, text, state=state, key=f"res_{q.id}_{key}")

    # 5. Explanation
    if fb.get("explanation"):
        st.info(f"{fb['explanation']}")

    # 6. Next Button
    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        callback("NEXT_QUESTION", None)
