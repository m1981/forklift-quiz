import streamlit as st
from src.game.core import UIModel
from src.quiz.presentation.views import components, question_view, summary_view


class StreamlitRenderer:
    """
    Translates Engine DTOs (UIModel) into Streamlit Widgets.
    """

    def render(self, ui_model: UIModel, callback_handler):
        """
        :param ui_model: Data from the engine.
        :param callback_handler: Function to call when user clicks buttons.
        """
        if not ui_model:
            st.spinner("Loading...")
            return

        step_type = ui_model.type
        payload = ui_model.payload

        if step_type == "TEXT":
            self._render_text_step(payload, callback_handler)
        elif step_type == "QUESTION":
            question_view.render_active(payload, callback_handler)
        elif step_type == "FEEDBACK":
            question_view.render_feedback(payload, callback_handler)
        elif step_type == "SUMMARY":
            summary_view.render(payload, callback_handler)
        elif step_type == "EMPTY":
            st.info("Flow Complete. Select a mode to start.")

        # --- FIX START: Add Handler for LOADING ---
        elif step_type == "LOADING":
            # This state happens when the app first loads but no flow is selected yet.
            st.info("👋 Witaj! Wybierz tryb z menu po lewej stronie, aby rozpocząć.")
        # --- FIX END ---

        else:
            st.error(f"Unknown Step Type: {step_type}")

    def _render_text_step(self, payload, callback):
        st.title(payload.title)
        st.markdown(payload.content)
        if payload.image_path:
            st.image(payload.image_path)

        if st.button(payload.button_text, type="primary"):
            callback("NEXT", None)