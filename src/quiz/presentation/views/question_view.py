import os
from collections.abc import Callable
from typing import Any

import streamlit as st


def _render_header(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """Helper to render the breadcrumbs and category progress."""

    # 1. Define the Breadcrumb Logic
    # We want: "🏠 Pulpit / Flow Title [/ Category Name]"

    col1, col2 = st.columns([3, 1])

    with col1:
        # We use columns inside to make the "Home" button sit inline with text
        # But Streamlit buttons are block elements.
        # A cleaner way is to use a small button for Home, then text.

        if st.button(
            "🏠 Pulpit",
            type="secondary",
            key="breadcrumb_home",
            help="Wróć do menu głównego",
        ):
            callback("NAVIGATE_HOME", None)
            return  # Stop rendering to prevent glitches during rerun

        # Construct the text path
        path_text = f"**{payload.flow_title}**"

        # Only append category if it's different from the flow title (ignoring emojis)
        # e.g. Flow="Daily Sprint", Cat="Hydraulics" -> Show both
        # e.g. Flow="Hydraulics", Cat="Hydraulics" -> Show only Flow
        clean_flow_title = (
            payload.flow_title.replace("📚 ", "").replace("🚀 ", "").strip()
        )

        if clean_flow_title != payload.category_name:
            path_text += f"  /  *{payload.category_name}*"

        st.markdown(path_text)

    with col2:
        # 2. Category Mastery Progress (Compact)
        pct = int(payload.category_mastery * 100)
        st.caption(f"Opanowanie: {pct}%")
        st.progress(payload.category_mastery)

    st.write("---")  # Separator


def render_active(payload: Any, callback: Callable[[str, Any], None]) -> None:
    # --- NEW HEADER ---
    _render_header(payload, callback)
    # ------------------

    q = payload.question

    # --- CSS FIX: Left Align & Text Wrap ---
    st.markdown(
        """
        <style>
            /* 1. Force the button to align its flex content to the start (left) */
            div[data-testid="stButton"] > button {
                width: 100% !important;
                justify-content: flex-start !important;
                text-align: left !important;
                height: auto !important;
                padding-top: 12px !important;
                padding-bottom: 12px !important;
            }

            /* 2. Force the inner text (paragraph) to align left */
            div[data-testid="stButton"] > button p {
                text-align: left !important;
                font-size: 1rem !important;
                white-space: normal !important; /* Ensure text wraps */
                word-wrap: break-word !important;
            }

            /* 3. Ensure the inner container takes full width */
            div[data-testid="stButton"] > button > div {
                width: 100% !important;
                justify-content: flex-start !important;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # --- Header ---
    st.markdown(f"### Pytanie {payload.current_index}/{payload.total_count}")
    st.markdown(f"**{q.text}**")

    # --- Image ---
    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # --- Options (Vertical Stack for correct order) ---
    st.write("---")

    options = list(q.options.items())

    # FIX: Removed 'enumerate' since 'idx' was unused
    for key, text in options:
        # Use full width container so it looks like a list
        if st.button(
            f"{key.value}) {text}", key=f"btn_{q.id}_{key}", use_container_width=True
        ):
            callback("SUBMIT_ANSWER", key)

    # --- Hint ---
    if q.hint:
        with st.expander("💡 Wskazówka"):
            st.info(q.hint)


def render_feedback(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """
    Renders the feedback screen with FROZEN options and color coding.
    """
    _render_header(payload, callback)
    q = payload.question
    fb = payload.last_feedback

    # 1. Header
    st.markdown(f"### Pytanie {payload.current_index}/{payload.total_count}")
    st.markdown(f"**{q.text}**")

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # 2. Status Message
    if fb["is_correct"]:
        st.success("✅ Dobra odpowiedź!")

    # 3. FROZEN OPTIONS VISUALIZATION
    st.write("---")

    for key, text in q.options.items():
        # Default styling
        prefix = "⚪"
        style_start = ""
        style_end = ""

        # Logic for coloring
        if key == fb["correct_option"]:
            prefix = "✅"
            style_start = ":green[**"
            style_end = "**]"
        elif key == fb["selected"] and not fb["is_correct"]:
            prefix = "❌"
            style_start = ":red[**"
            style_end = "**]"

        # Render as Markdown text (not buttons) so it's "frozen"
        st.markdown(f"{prefix} {style_start}{key.value}) {text}{style_end}")

    # 4. Explanation & Navigation
    st.write("")
    st.write("")

    if fb.get("explanation"):
        st.markdown(f"> **Wyjaśnienie:** {fb['explanation']}")
        st.write("")  # Spacer

    # 5. Navigation Button
    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        callback("NEXT_QUESTION", None)
