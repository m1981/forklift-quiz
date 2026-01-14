import pytest
from unittest.mock import Mock, patch, MagicMock
from src.game.core import UIModel
from src.game.steps import SummaryPayload
from src.quiz.presentation.renderer import StreamlitRenderer

class TestRendererInteractions:
    """
    Focuses on: "If I click a button, does the callback fire?"
    """

    @pytest.fixture
    def mock_streamlit(self):
        with patch('src.quiz.presentation.renderer.st') as mock_st:
            with patch('src.quiz.presentation.views.summary_view.st') as s_st:

                # <--- FIX: Dynamic Column Generation
                # This ensures st.columns(2) returns 2 mocks, and st.columns(3) returns 3 mocks.
                def create_cols(spec=1, *args, **kwargs):
                    count = spec if isinstance(spec, int) else len(spec)
                    return [MagicMock() for _ in range(count)]

                # Apply side effect to all column calls
                mock_st.columns.side_effect = create_cols
                s_st.columns.side_effect = create_cols

                yield mock_st, s_st

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    def test_summary_view_finish_button_triggers_callback(self, renderer, mock_streamlit):
        # Arrange
        _, s_st = mock_streamlit
        mock_callback = Mock()

        # SIMULATE USER CLICK: The first button (Menu) returns True
        s_st.button.side_effect = [True, False]

        payload = SummaryPayload(score=10, total=10, message="Done", has_errors=False)
        model = UIModel(type="SUMMARY", payload=payload)

        # Act
        renderer.render(model, mock_callback)

        # Assert
        mock_callback.assert_called_with("FINISH", None)

    def test_summary_view_review_button_triggers_callback(self, renderer, mock_streamlit):
        # Arrange
        _, s_st = mock_streamlit
        mock_callback = Mock()

        # SIMULATE USER CLICK:
        # Call 1 (Menu): False, Call 2 (Review): True
        s_st.button.side_effect = [False, True]

        # We must have errors for the button to appear
        payload = SummaryPayload(score=5, total=10, message="Fail", has_errors=True)
        model = UIModel(type="SUMMARY", payload=payload)

        # Act
        renderer.render(model, mock_callback)

        # Assert
        mock_callback.assert_called_with("REVIEW_MISTAKES", None)

    def test_renderer_handles_loading_state(self, renderer, mock_streamlit):
        # Arrange
        mock_st, _ = mock_streamlit
        model = UIModel(type="LOADING", payload={})

        # Act
        renderer.render(model, Mock())

        # Assert
        # The implementation uses st.info("Wczytywanie...")
        mock_st.info.assert_called()