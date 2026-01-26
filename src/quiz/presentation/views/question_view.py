import os
from collections.abc import Callable
from typing import Any

import streamlit as st

from src.components.mobile_suite import mobile_header, mobile_option


def _render_compact_header(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """
    Renders the V2 Mobile Header.
    Merges: Home Button + Question Counter + Category Name + Progress Bar
    into a single 40px high row.
    """
    # 1. Prepare Context Text (e.g. "1/15 • Hydraulika...")
    cat_name = payload.category_name
    # Truncate long category names to fit on mobile screens
    if len(cat_name) > 40:
        cat_name = cat_name[:40] + "..."

    context_text = f"{payload.current_index}/{payload.total_count} • {cat_name}"

    # 2. Render Component
    # If the user clicks the Home icon inside the component, it returns True
    if mobile_header(
        context=context_text, progress=payload.category_mastery, key="mob_header"
    ):
        callback("NAVIGATE_HOME", None)


def render_active(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """
    Renders the active question screen using optimized mobile components.
    """
    # 1. Header (Zero vertical waste)
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

    # 3. Image (Optional)
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # 4. Options (The Interactive V2 Components)
    # These replace st.button. They are tighter and touch-optimized.
    for key, text in q.options.items():
        # mobile_option returns the key_char (e.g. 'A') if clicked
        clicked_key = mobile_option(key.value, text, key=f"opt_{q.id}_{key}")

        if clicked_key:
            callback("SUBMIT_ANSWER", key)

    # 5. Hint (Bottom)
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

    # 2. Question Text (Repeated for context)
    st.markdown(f"**{q.text}**")

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # 3. Status Message (Compact)
    if fb["is_correct"]:
        st.success("✅ Dobrze!")
    else:
        st.error("❌ Źle")

    # 4. Frozen Options (Visualizing the result)
    # We use standard Markdown here to distinguish "Result" from "Input"
    for key, text in q.options.items():
        prefix = "⚪"
        style_start = ""
        style_end = ""

        if key == fb["correct_option"]:
            prefix = "✅"
            style_start = ":green[**"
            style_end = "**]"
        elif key == fb["selected"] and not fb["is_correct"]:
            prefix = "❌"
            style_start = ":red[**"
            style_end = "**]"

        st.markdown(f"{prefix} {style_start}{key.value}) {text}{style_end}")

    # 5. Explanation
    if fb.get("explanation"):
        st.info(f"{fb['explanation']}")

    # 6. Next Button
    # We keep this as a standard primary button as it's the main flow action
    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        callback("NEXT_QUESTION", None)
