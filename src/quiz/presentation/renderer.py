import math
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import streamlit as st

from src.components.mobile_suite import mobile_dashboard, mobile_hero
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
        # 1. Fetch Data
        director = st.session_state.game_director
        repo = director.context.repo
        user_id = director.context.user_id
        stats = repo.get_category_stats(user_id)

        # 2. Calculate Global Stats
        total_q = sum(s["total"] for s in stats)
        total_mastered = sum(s["mastered"] for s in stats)
        remaining = total_q - total_mastered
        days_left = math.ceil(remaining / 15) if remaining > 0 else 0
        finish_date = date.today() + timedelta(days=days_left)

        # Calculate progress float (0.0 - 1.0)
        global_progress = total_mastered / total_q if total_q > 0 else 0

        # --- 3. RENDER HERO (New Custom Component) ---
        # This replaces st.title, st.progress, and st.columns/st.metric
        mobile_hero(
            progress=global_progress,
            mastered_count=total_mastered,
            total_count=total_q,
            finish_date_str=finish_date.strftime("%d %b"),
            days_left=days_left,
            key="hero_stats",
        )

        # --- 4. RENDER DASHBOARD GRID ---
        # Prepare data for the component
        cat_data = []
        for stat in stats:
            cat_data.append(
                {
                    "name": stat["category"],
                    "progress": stat["mastered"] / stat["total"]
                    if stat["total"] > 0
                    else 0,
                    "icon": Category.get_icon(stat["category"]),
                }
            )

        # Render the Grid
        action = mobile_dashboard(categories=cat_data, key="mob_dash")

        # Handle Actions
        if action:
            if action["type"] == "SPRINT":
                callback("START_SPRINT_MANUAL", None)
            elif action["type"] == "CATEGORY":
                st.session_state["selected_category_manual"] = action["payload"]
                callback("START_CATEGORY_MANUAL", action["payload"])

            st.rerun()
