import math
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import streamlit as st

from src.components.category_button import category_button
from src.config import Category
from src.game.core import UIModel
from src.quiz.presentation.views import question_view, summary_view
from src.shared.telemetry import Telemetry


class StreamlitRenderer:
    """
    Translates Engine DTOs (UIModel) into Streamlit Widgets.
    """

    def __init__(self) -> None:
        self.telemetry = Telemetry("StreamlitRenderer")

    def render(
        self, ui_model: UIModel | None, callback_handler: Callable[[str, Any], None]
    ) -> None:
        if not ui_model:
            self.telemetry.log_info("UI Model is None. Rendering fallback.")
            st.warning("Inicjalizacja widoku...")
            return

        step_type = ui_model.type
        payload = ui_model.payload

        # <--- LOGGING THE STATE
        self.telemetry.log_info(
            f"Rendering Step: {step_type}",
            payload_keys=list(payload.__dict__.keys())
            if hasattr(payload, "__dict__")
            else "dict",
        )

        if step_type == "TEXT":
            self._render_text_step(payload, callback_handler)
        elif step_type == "QUESTION":
            question_view.render_active(payload, callback_handler)
        elif step_type == "FEEDBACK":
            question_view.render_feedback(payload, callback_handler)
        elif step_type == "SUMMARY":
            summary_view.render(payload, callback_handler)
        elif step_type == "EMPTY":
            self._render_dashboard(callback_handler)
        elif step_type == "LOADING":
            st.info("Wczytywanie...")
        else:
            self.telemetry.log_error(
                f"Unknown Step Type: {step_type}", Exception("Renderer Error")
            )
            st.error(f"Unknown Step Type: {step_type}")

    def _render_text_step(
        self, payload: Any, callback: Callable[[str, Any], None]
    ) -> None:
        st.title(payload.title)
        st.markdown(payload.content)
        if payload.image_path:
            st.image(payload.image_path)

        if st.button(payload.button_text, type="primary"):
            callback("NEXT", None)

    def _render_dashboard(self, callback: Callable[[str, Any], None]) -> None:
        # 1. Fetch Data (pass via ViewModel in production)
        # We assume 'st.session_state.game_director' exists
        director = st.session_state.game_director
        repo = director.context.repo
        user_id = director.context.user_id

        stats = repo.get_category_stats(user_id)

        # 2. Calculate Global Stats
        total_q = sum(s["total"] for s in stats)
        total_mastered = sum(s["mastered"] for s in stats)
        remaining = total_q - total_mastered

        # Prediction: 15 questions per day
        days_left = math.ceil(remaining / 15) if remaining > 0 else 0
        finish_date = date.today() + timedelta(days=days_left)

        # --- HERO SECTION (Global Progress) ---
        st.title("👋 Centrum Dowodzenia")

        # Progress Bar
        progress = total_mastered / total_q if total_q > 0 else 0
        st.progress(
            progress, text=f"Globalne Opanowanie Materiału: {int(progress * 100)}%"
        )

        # Prediction Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Opanowane Pytania", f"{total_mastered} / {total_q}")
        with col2:
            st.metric(
                "Przewidywany Koniec",
                finish_date.strftime("%d %b %Y"),
                f"za {days_left} dni",
            )

        st.write("")  # Spacer

        # --- SECTION 1: THE DAILY FLOW ---
        # We use a container to visually group the "Daily" task
        with st.container(border=True):
            st.subheader("🚀 Twój Cel na Dziś")
            st.caption("Algorytm dobierze 15 pytań: 60% nowych + 40% powtórek.")

            if st.button(
                "ROZPOCZNIJ SPRINT (15 Pytań)", type="primary", use_container_width=True
            ):
                callback("START_SPRINT_MANUAL", None)

        st.write("")
        st.markdown("### — LUB —")
        st.write("")

        # --- SECTION 2: THE CATEGORY FLOW ---
        st.subheader("📚 Trenuj Konkretne Działy")
        st.caption("Wybierz kategorię, aby nadrobić zaległości lub wymaksować wynik.")

        # Create a grid layout (2 columns)
        cols = st.columns(2)

        for idx, stat in enumerate(stats):
            cat_name = stat["category"]
            cat_total = stat["total"]
            cat_mastered = stat["mastered"]
            cat_progress = cat_mastered / cat_total if cat_total > 0 else 0

            # Visual Logic
            is_mastered = cat_progress >= 1.0
            pct_str = f"{int(cat_progress * 100)}%"

            # --- ICON LOGIC (DRY) ---
            if is_mastered:
                icon = "✅"
            else:
                # Look up the icon using the Enum helper method
                icon = Category.get_icon(cat_name)

            with cols[idx % 2]:
                clicked_id = category_button(
                    id=cat_name,
                    label=cat_name,
                    progress=pct_str,
                    icon=icon,
                    key=f"cat_btn_{idx}",
                )

                if clicked_id:
                    st.session_state["selected_category_manual"] = clicked_id
                    callback("START_CATEGORY_MANUAL", clicked_id)
                    st.rerun()

        # --- FOOTER (Optional) ---
        st.markdown("---")
        if st.button("🎓 Powtórz Wprowadzenie (Tutorial)", type="secondary"):
            callback("START_ONBOARDING_MANUAL", None)
