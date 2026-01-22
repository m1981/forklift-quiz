import streamlit as st
from src.game.core import UIModel
from src.quiz.presentation.views import question_view, summary_view
from src.shared.telemetry import Telemetry  # <--- NEW IMPORT


class StreamlitRenderer:
    """
    Translates Engine DTOs (UIModel) into Streamlit Widgets.
    """
    def __init__(self):
        self.telemetry = Telemetry("StreamlitRenderer")

    def render(self, ui_model: UIModel, callback_handler):
        if not ui_model:
            self.telemetry.log_info("UI Model is None. Rendering fallback.")
            st.warning("Inicjalizacja widoku...")
            return

        step_type = ui_model.type
        payload = ui_model.payload

        # <--- LOGGING THE STATE
        self.telemetry.log_info(f"Rendering Step: {step_type}", payload_keys=list(payload.__dict__.keys()) if hasattr(payload, '__dict__') else "dict")

        if step_type == "TEXT":
            self._render_text_step(payload, callback_handler)
        elif step_type == "QUESTION":
            question_view.render_active(payload, callback_handler)
        elif step_type == "FEEDBACK":
            question_view.render_feedback(payload, callback_handler)
        elif step_type == "SUMMARY":
            summary_view.render(payload, callback_handler)
        elif step_type == "EMPTY":
            # --- IMPROVED EMPTY STATE ---
            st.title("Gotowy do pracy?")
            # st.markdown("### Co chcesz teraz zrobić?")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Rozpocznij Naukę", type="primary", use_container_width=True):
                    callback_handler("START_SPRINT_MANUAL", None)
            with col2:
                if st.button("🎓 Powtórz Wprowadzenie", type="secondary", use_container_width=True):
                    callback_handler("START_ONBOARDING_MANUAL", None)

        # <--- FIX: HANDLE LOADING STATE
        elif step_type == "LOADING":
            st.info("Wczytywanie...") # Use st.info instead of spinner for visibility
        else:
            self.telemetry.log_error(f"Unknown Step Type: {step_type}", Exception("Renderer Error"))
            st.error(f"Unknown Step Type: {step_type}")

    def _render_text_step(self, payload, callback):
        st.title(payload.title)
        st.markdown(payload.content)
        if payload.image_path:
            st.image(payload.image_path)

        if st.button(payload.button_text, type="primary"):
            callback("NEXT", None)