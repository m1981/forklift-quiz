import pytest
from unittest.mock import Mock, patch, MagicMock
from src.game.core import UIModel
from src.game.steps import SummaryPayload
from src.quiz.presentation.renderer import StreamlitRenderer


class TestSummaryViewInteractions:
    """
    Targeted tests for src/quiz/presentation/views/summary_view.py
    Focus: Lines 33-34 (Finish) and 39-40 (Review)
    """

    @pytest.fixture
    def mock_dependencies(self):
        # We patch the 'st' object specifically inside the summary_view module
        with patch('src.quiz.presentation.views.summary_view.st') as mock_st:
            # 1. Handle st.columns()
            # summary_view calls columns(3) for metrics, then columns(2) for buttons.
            # We need a side_effect to return the right amount of MagicMocks (for 'with' context)
            def create_cols(count):
                return [MagicMock() for _ in range(count)]

            mock_st.columns.side_effect = create_cols

            yield mock_st

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    def test_finish_button_click_triggers_callback(self, renderer, mock_dependencies):
        """
        Covers Lines 33-34:
        if st.button("🔄 Menu Główne"...):
            callback("FINISH", None)
        """
        mock_st = mock_dependencies
        mock_callback = Mock()

        # ARRANGE
        # We simulate the user clicking the FIRST button ("Menu Główne")
        # side_effect = [True] means the first call to st.button returns True.
        mock_st.button.side_effect = [True, False]

        payload = SummaryPayload(score=10, total=10, message="Good", has_errors=False)
        model = UIModel(type="SUMMARY", payload=payload)

        # ACT
        renderer.render(model, mock_callback)

        # ASSERT
        # 1. Verify we entered the 'if' block
        mock_callback.assert_called_once_with("FINISH", None)

    def test_review_button_click_triggers_callback(self, renderer, mock_dependencies):
        """
        Covers Lines 39-40:
        if st.button("🛠️ Popraw Błędy"...):
            callback("REVIEW_MISTAKES", None)
        """
        mock_st = mock_dependencies
        mock_callback = Mock()

        # ARRANGE
        # 1. We need has_errors=True to even render the button
        payload = SummaryPayload(score=5, total=10, message="Bad", has_errors=True)
        model = UIModel(type="SUMMARY", payload=payload)

        # 2. Simulate Button Clicks
        # The view renders "Menu Główne" first, then "Popraw Błędy".
        # We want to ignore the first (False) and click the second (True).
        mock_st.button.side_effect = [False, True]

        # ACT
        renderer.render(model, mock_callback)

        # ASSERT
        # 1. Verify we entered the nested 'if' block
        mock_callback.assert_called_once_with("REVIEW_MISTAKES", None)

    def test_review_button_not_shown_if_no_errors(self, renderer, mock_dependencies):
        """
        Edge Case: Ensure we don't try to click a button that shouldn't exist.
        """
        mock_st = mock_dependencies
        mock_callback = Mock()

        # ARRANGE
        payload = SummaryPayload(score=10, total=10, message="Perfect", has_errors=False)
        model = UIModel(type="SUMMARY", payload=payload)

        # ACT
        renderer.render(model, mock_callback)

        # ASSERT
        # Only one button ("Menu") should have been rendered
        assert mock_st.button.call_count == 1