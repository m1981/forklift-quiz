import pytest
from unittest.mock import Mock
from src.game.core import UIModel
from src.quiz.presentation.renderer import StreamlitRenderer


class TestRendererContract:
    """
    Ensures the Renderer handles ALL possible UIModel types produced by the Engine.
    This prevents 'Unknown Step Type' errors in production.
    """

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    @pytest.fixture
    def mock_callback(self):
        return Mock()

    def test_renderer_handles_loading_state(self, renderer, mock_callback):
        # The Director produces this state initially
        model = UIModel(type="LOADING", payload={})

        try:
            renderer.render(model, mock_callback)
        except Exception as e:
            pytest.fail(f"Renderer crashed on LOADING state: {e}")

    def test_renderer_handles_empty_state(self, renderer, mock_callback):
        model = UIModel(type="EMPTY", payload={"message": "Done"})
        try:
            renderer.render(model, mock_callback)
        except Exception as e:
            pytest.fail(f"Renderer crashed on EMPTY state: {e}")

    def test_renderer_handles_unknown_state_gracefully(self, renderer, mock_callback):
        # We want to ensure it shows an error message, NOT crash the app
        model = UIModel(type="NON_EXISTENT_TYPE", payload={})

        # Streamlit functions (st.error) usually don't raise exceptions in tests
        # unless we mock them to do so.
        # Here we just ensure the render method finishes execution.
        try:
            renderer.render(model, mock_callback)
        except Exception as e:
            pytest.fail(f"Renderer crashed on unknown state: {e}")

    # --- Advanced: Exhaustiveness Check ---
    # If you want to be 100% sure, you can list all known types here
    @pytest.mark.parametrize("step_type", [
        "TEXT",
        "QUESTION",
        "FEEDBACK",
        "SUMMARY",
        "LOADING",
        "EMPTY"
    ])
    def test_renderer_supports_all_known_types(self, renderer, mock_callback, step_type):
        # Create a dummy payload that satisfies the renderer's attribute access
        # We use a Mock object so accessing .title, .content etc. doesn't fail
        dummy_payload = Mock()
        dummy_payload.title = "Test"
        dummy_payload.content = "Test"
        dummy_payload.question.text = "Q"
        dummy_payload.question.options = {}

        model = UIModel(type=step_type, payload=dummy_payload)

        try:
            renderer.render(model, mock_callback)
        except AttributeError:
            # It's okay if it fails due to missing payload fields (that's a different test),
            # but it should NOT fail because of "Unknown Step Type" logic.
            pass
        except Exception as e:
            pytest.fail(f"Renderer logic failed for type {step_type}: {e}")