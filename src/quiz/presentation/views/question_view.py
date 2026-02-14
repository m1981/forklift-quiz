import os
from typing import Any

import streamlit as st

from src.components.mobile import mobile_header, mobile_option, mobile_result_row
from src.quiz.domain.models import Language, Question


def render_quiz_screen(service: Any, user_id: str) -> None:
    """
    Main entry point for the Quiz Screen.
    Orchestrates rendering based on session state (Active vs Feedback).
    """
    # 1. Get State from Session
    if "quiz_questions" not in st.session_state or not st.session_state.quiz_questions:
        st.error("Brak pytań w sesji. Powrót do menu.")
        st.session_state.screen = "dashboard"
        st.rerun()

    idx = st.session_state.current_index
    questions = st.session_state.quiz_questions
    question: Question = questions[idx]

    # Cache profile in session state
    if "cached_profile" not in st.session_state:
        st.session_state.cached_profile = service.profile_manager.get()

    profile = st.session_state.cached_profile
    user_lang = profile.preferred_language

    # 3. Calculate Progress for Header
    total = len(questions)
    # Calculate mastery for the current category on the fly
    # (Optional optimization: cache this in session state if it's too slow)
    category_mastery = service.repo.get_mastery_percentage(user_id, question.category)

    # 4. Render Header
    _render_compact_header(idx + 1, total, question.category, category_mastery)

    # 5. Render Content (Active Question or Feedback)
    if st.session_state.get("feedback_mode", False):
        _render_feedback(service, question, user_lang)
    else:
        _render_active(service, user_id, question, user_lang)


def _render_compact_header(
    current_idx: int, total: int, category: str, mastery: float
) -> None:
    if len(category) > 40:
        category = category[:40] + "..."

    context_text = f"{current_idx}/{total} • {category}"

    # mobile_header returns True if "Home" is clicked
    if mobile_header(context=context_text, progress=mastery, key="mob_header"):
        st.session_state.screen = "dashboard"
        st.rerun()


def _render_active(
    service: Any, user_id: str, q: Question, user_lang: Language
) -> None:
    # 1. Question Text (ALWAYS POLISH - Source of Truth)
    st.markdown(
        f"""
        <div style="
            font-size: 16px;  /* Increased from 1rem (16px) */
            font-weight: 600; /* Medium weight for emphasis */
            color: #111827;
            margin-top: 10px;
            margin-bottom: 20px; /* More breathing room */
            line-height: 1.6;    /* Improved readability */
            letter-spacing: -0.011em;">
            {q.id}: {q.text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if q.image_path and os.path.exists(q.image_path):
        st.image(q.image_path, use_container_width=True)

    # 2. Options (ALWAYS POLISH - Source of Truth)
    for key, text in q.options.items():
        # mobile_option returns the key (e.g., "A") if clicked
        clicked_key = mobile_option(key.value, text, key=f"opt_{q.id}_{key}")

        if clicked_key:
            # --- DIRECT SERVICE CALL ---
            service.submit_answer(user_id, q, key)
            st.rerun()

    # 3. Hint (Persisted Language Selection)
    if q.hint:
        with st.expander("💡 Wskazówka"):
            # A. Identify available languages
            available_langs = [Language.PL]
            for lang, content in q.translations.items():
                if content.hint:
                    available_langs.append(lang)

            # B. If multiple languages, show selector that UPDATES DB
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
                if selected_lang is not None and selected_lang != user_lang:
                    # --- DIRECT SERVICE CALL ---
                    service.update_language(user_id, selected_lang.value)
                    # Service handles rerun, but we can do it here to be explicit
                    st.rerun()

                # Handle None case (if user deselects) -> fallback to default
                display_lang = selected_lang if selected_lang else default_selection
                st.info(q.get_hint(display_lang))

            else:
                # Only Polish available
                st.info(q.hint)


def _render_feedback(service: Any, q: Question, user_lang: Language) -> None:
    """
    Renders the feedback screen using the new Gentle Result Rows.
    """
    # Retrieve feedback data from session state
    fb = st.session_state.last_feedback

    # Question Text (Polish)
    st.markdown(f"{q.id}: {q.text}")

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

    # Hint (collapsed) - Show what was available
    if q.hint:
        with st.expander("💡 Wskazówka"):
            hint_text = q.get_hint(user_lang)
            st.info(hint_text)

    # Explanation (TRANSLATED) - expanded
    expl_text = q.get_explanation(user_lang)

    if expl_text:
        with st.expander("📖 Wyjaśnienie", expanded=True):
            st.info(expl_text)

            # If showing translation, offer original
            if user_lang != Language.PL and expl_text != q.explanation:
                with st.expander("🇵🇱 Pokaż wyjaśnienie po polsku"):
                    st.write(q.explanation)

    if st.button("Dalej ➡️", type="primary", use_container_width=True):
        service.next_question()
        st.rerun()
