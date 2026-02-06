import os
from collections.abc import Callable
from typing import Any

import streamlit as st

from src.components.mobile import mobile_header, mobile_option, mobile_result_row
from src.quiz.domain.models import Language


def _render_compact_header(payload: Any, callback: Callable[[str, Any], None]) -> None:
    cat_name = payload.category_name
    if len(cat_name) > 40:
        cat_name = cat_name[:40] + "..."

    context_text = f"{payload.current_index}/{payload.total_count} • {cat_name}"

    if mobile_header(
        context=context_text, progress=payload.category_mastery, key="mob_header"
    ):
        callback("NAVIGATE_HOME", None)


def render_active(payload: Any, callback: Callable[[str, Any], None]) -> None:
    _render_compact_header(payload, callback)

    q = payload.question
    lang = payload.preferred_language

    # 1. Question Text (ALWAYS POLISH - Source of Truth)
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

    # 2. Options (ALWAYS POLISH - Source of Truth)
    for key, text in q.options.items():
        clicked_key = mobile_option(key.value, text, key=f"opt_{q.id}_{key}")
        if clicked_key:
            callback("SUBMIT_ANSWER", key)

    # 3. Hint (TRANSLATED)
    # Logic: Get translated hint. If user is foreign AND translation exists,
    # show translation + expander for original.
    hint_text = q.get_hint(lang)

    if hint_text:
        with st.expander("💡 Wskazówka"):
            st.info(hint_text)

            # If we are showing a translation, offer the original
            if lang != Language.PL and hint_text != q.hint:
                st.caption("🇵🇱 Oryginał:")
                st.text(q.hint)


def render_feedback(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """
    Renders the feedback screen using the new Gentle Result Rows.
    """
    _render_compact_header(payload, callback)

    q = payload.question
    fb = payload.last_feedback
    lang = payload.preferred_language

    # Question Text (Polish)
    st.markdown(f"{q.text}")

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # Result Rows (Polish)
    for key, text in q.options.items():
        state = "neutral"
        if key == fb["correct_option"]:
            state = "correct" if key == fb["selected"] else "missed"
        elif key == fb["selected"] and not fb["is_correct"]:
            state = "wrong"

        mobile_result_row(key.value, text, state=state, key=f"res_{q.id}_{key}")

    # Explanation (TRANSLATED)
    expl_text = q.get_explanation(lang)

    if expl_text:
        # Main explanation box
        st.info(f"{expl_text}")

        # If we are showing a translation, offer the original
        if lang != Language.PL and expl_text != q.explanation:
            with st.expander("🇵🇱 Pokaż wyjaśnienie po polsku"):
                st.write(q.explanation)

    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        callback("NEXT_QUESTION", None)
