from collections.abc import Callable
from typing import Any

import streamlit as st

from src.components.mobile import mobile_dashboard, mobile_hero
from src.config import GameConfig
from src.game.core import UIModel
from src.quiz.presentation.views import question_view, summary_view
from src.shared.telemetry import Telemetry

# --- ADR 005: Passive View Pattern ---
# Decision: The Renderer MUST NOT perform business logic, data fetching,
# or complex calculations.
# Rationale: Logic leaking into the View makes the application hard to test
# and violates SoC. The Renderer's sole responsibility is to map the
# `UIModel` (DTO) to Streamlit widgets.
# All calculations (dates, progress math) must happen in the `GameStep`.
# -------------------------------------


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

        if ui_model.branding_logo_path and hasattr(payload, "app_logo_src"):
            payload.app_logo_src = GameConfig.get_image_base64(
                ui_model.branding_logo_path
            )

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
        elif step_type == "DASHBOARD":  # <--- Changed from EMPTY
            self._render_dashboard(payload, callback_handler)
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

    def _render_dashboard(
        self, payload: Any, callback: Callable[[str, Any], None]
    ) -> None:
        # Let's assume standard payload usage:
        logo_to_render = payload.app_logo_src

        # 1. RENDER HERO
        mobile_hero(
            title=payload.app_title,
            logo_src=logo_to_render,
            progress=payload.global_progress,
            mastered_count=payload.total_mastered,
            total_count=payload.total_questions,
            finish_date_str=payload.finish_date_str,
            days_left=payload.days_left,
            key="hero_stats",
        )

        # 2. RENDER DASHBOARD GRID
        action = mobile_dashboard(payload.categories)
        # Handle Actions
        if action:
            if action["type"] == "SPRINT":
                callback("START_SPRINT_MANUAL", None)
            elif action["type"] == "CATEGORY":
                st.session_state["selected_category_manual"] = action["payload"]
                callback("START_CATEGORY_MANUAL", action["payload"])

            st.rerun()
