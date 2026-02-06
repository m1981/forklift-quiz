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
    user_lang = payload.preferred_language

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

    # 3. Hint (Always show pills if translations exist)
    # Check if the base Polish hint exists
    if q.hint:
        with st.expander("💡 Wskazówka", expanded=True):
            # A. Identify which languages have a hint defined
            # Polish is always available if q.hint exists
            available_langs = [Language.PL]

            # Check translations dictionary
            for lang, content in q.translations.items():
                if content.hint:
                    available_langs.append(lang)

            # B. If we have more than just Polish, show the selector
            if len(available_langs) > 1:
                # Helper for labels
                def format_lang(lang: Language) -> str:
                    if lang == Language.PL:
                        return "🇵🇱 Polski"
                    if lang == Language.EN:
                        return "🇬🇧 English"
                    if lang == Language.UK:
                        return "🇺🇦 Українська"
                    if lang == Language.KA:
                        return "🇬🇪 ქართული"
                    return lang.value.upper()

                # Determine default
                default_selection = (
                    user_lang if user_lang in available_langs else Language.PL
                )

                # Unique key for this widget
                pill_key = f"hint_pill_{q.id}"

                # Render Pills
                selected_lang = st.pills(
                    "Język / Language",
                    options=available_langs,
                    format_func=format_lang,
                    default=default_selection,
                    selection_mode="single",
                    label_visibility="collapsed",
                    key=pill_key,
                )

                # Linear Check: If value changed, trigger action immediately.
                # This runs in the main script flow, so st.rerun() inside callback() is valid.
                if selected_lang is not None and selected_lang != user_lang:
                    callback("CHANGE_LANGUAGE", selected_lang.value)

                # Handle None case (if user deselects) -> fallback to default
                display_lang = selected_lang if selected_lang else default_selection

                st.info(q.get_hint(display_lang))

            else:
                # Only Polish available, just show text
                st.info(q.hint)


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
