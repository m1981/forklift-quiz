import logging
import os
from collections.abc import Callable
from typing import Any

import streamlit as st

from src.components.mobile import mobile_header, mobile_option, mobile_result_row
from src.quiz.domain.models import Language

logger = logging.getLogger(__name__)


def _render_compact_header(payload: Any, callback: Callable[[str, Any], None]) -> None:
    cat_name = payload.category_name
    if len(cat_name) > 40:
        cat_name = cat_name[:40] + "..."

    context_text = f"{payload.current_index}/{payload.total_count} • {cat_name}"

    if mobile_header(
        context=context_text, progress=payload.category_mastery, key="mob_header"
    ):
        callback("NAVIGATE_HOME", None)


def _render_hint_section(
    q: Any,
    user_lang: Language,
    callback: Callable[[str, Any], None],
    default_expanded: bool = False,  # <--- Added parameter
) -> None:
    """
    Shared logic to render the Hint section with Pills and Dual Display.
    """
    if not q.hint:
        return

    # Pass the expanded state to the expander
    with st.expander("💡 Wskazówka", expanded=default_expanded):
        available_langs = [Language.PL]
        for lang, content in q.translations.items():
            if content.hint:
                available_langs.append(lang)

        if len(available_langs) > 1:

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

            default_selection = (
                user_lang if user_lang in available_langs else Language.PL
            )
            pill_key = f"hint_pill_{q.id}"

            selected_lang = st.pills(
                "Język / Language",
                options=available_langs,
                format_func=format_lang,
                default=default_selection,
                selection_mode="single",
                label_visibility="collapsed",
                key=pill_key,
            )

            if selected_lang is not None and selected_lang != user_lang:
                callback("CHANGE_LANGUAGE", selected_lang.value)

            display_lang = selected_lang if selected_lang else default_selection

            # Display Translated
            st.info(q.get_hint(display_lang))

            # Display Original if different
            if display_lang != Language.PL:
                st.caption("🇵🇱 Oryginał:")
                st.markdown(f"_{q.hint}_")

        else:
            st.info(q.hint)


def render_active(payload: Any, callback: Callable[[str, Any], None]) -> None:
    _render_compact_header(payload, callback)

    q = payload.question
    user_lang = payload.preferred_language

    # 1. Question Text
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

    # 2. Options
    for key, text in q.options.items():
        clicked_key = mobile_option(key.value, text, key=f"opt_{q.id}_{key}")
        if clicked_key:
            callback("SUBMIT_ANSWER", key)

    # 3. Hint (Shared Logic)
    # In active view, we keep it collapsed by default (standard behavior)
    _render_hint_section(q, user_lang, callback, default_expanded=False)


def render_feedback(payload: Any, callback: Callable[[str, Any], None]) -> None:
    """
    Renders the feedback screen using the new Gentle Result Rows.
    """
    _render_compact_header(payload, callback)

    q = payload.question
    fb = payload.last_feedback
    user_lang = payload.preferred_language

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

    # --- 1. HINT SECTION ---
    # Explicitly force collapsed state in feedback view
    _render_hint_section(q, user_lang, callback, default_expanded=False)

    # --- 2. EXPLANATION SECTION ---
    if q.explanation:
        st.markdown("### 📖 Wyjaśnienie")

        # A. Identify which languages have an EXPLANATION defined
        available_langs = [Language.PL]
        for lang, content in q.translations.items():
            if content.explanation:
                available_langs.append(lang)

        # B. If we have more than just Polish, show the selector
        if len(available_langs) > 1:

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

            default_selection = (
                user_lang if user_lang in available_langs else Language.PL
            )

            # Unique key for explanation pills
            pill_key = f"expl_pill_{q.id}"

            selected_lang = st.pills(
                "Język / Language",
                options=available_langs,
                format_func=format_lang,
                default=default_selection,
                selection_mode="single",
                label_visibility="collapsed",
                key=pill_key,
            )

            # Persistence Logic
            if selected_lang is not None and selected_lang != user_lang:
                callback("CHANGE_LANGUAGE", selected_lang.value)

            display_lang = selected_lang if selected_lang else default_selection

            # 1. Display Translated Text
            st.info(q.get_explanation(display_lang))

            # 2. Display Original if different
            if display_lang != Language.PL:
                st.caption("🇵🇱 Oryginał:")
                st.markdown(f"{q.explanation}")

        else:
            # Only Polish available
            st.info(q.explanation)

    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        callback("NEXT_QUESTION", None)
