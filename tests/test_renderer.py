from unittest.mock import MagicMock, Mock, patch

import pytest

from src.game.core import UIModel
from src.game.steps import SummaryPayload
from src.quiz.presentation.renderer import StreamlitRenderer


class TestRendererInteractions:
    """
    Focuses on: "If I click a button, does the callback fire?"
    """

    @pytest.fixture
    def mock_streamlit(self):
        """
        Patches Streamlit at the renderer and view levels.
        Also mocks session_state for the Dashboard.
        """
        with patch("src.quiz.presentation.renderer.st") as mock_st:
            with patch("src.quiz.presentation.views.summary_view.st") as s_st:
                # 1. Handle Dynamic Columns (2 or 3 cols)
                def create_cols(spec=1, *args, **kwargs):
                    count = spec if isinstance(spec, int) else len(spec)
                    return [MagicMock() for _ in range(count)]

                mock_st.columns.side_effect = create_cols
                s_st.columns.side_effect = create_cols

                # 2. Mock Session State (Critical for Dashboard)
                # The renderer accesses st.session_state.game_director.context.repo
                mock_director = MagicMock()
                mock_repo = MagicMock()

                # Setup the chain: director -> context -> repo
                mock_director.context.repo = mock_repo
                mock_director.context.user_id = "TestUser"

                # Mock repo stats response
                mock_repo.get_category_stats.return_value = [
                    {"category": "BHP", "total": 10, "mastered": 5}
                ]

                mock_st.session_state.game_director = mock_director

                yield mock_st, s_st

    @pytest.fixture
    def mock_components(self):
        """
        Patches the custom mobile components used in the dashboard.
        """
        with patch("src.quiz.presentation.renderer.mobile_hero") as mock_hero:
            with patch("src.quiz.presentation.renderer.mobile_dashboard") as mock_dash:
                yield mock_hero, mock_dash

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    def test_summary_view_finish_button_triggers_callback(
        self, renderer, mock_streamlit
    ):
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

    def test_summary_view_review_button_triggers_callback(
        self, renderer, mock_streamlit
    ):
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
        mock_st.info.assert_called()

    def test_dashboard_sprint_action(self, renderer, mock_streamlit, mock_components):
        """
        Verifies that clicking the 'Sprint' card on the dashboard
        triggers the correct action.
        """
        # Arrange
        mock_st, _ = mock_streamlit
        mock_hero, mock_dash = mock_components
        mock_callback = Mock()

        # Setup Component Returns
        mock_hero.return_value = None  # No action on hero

        # SIMULATE USER CLICK: The dashboard returns a SPRINT action
        mock_dash.return_value = {"type": "SPRINT", "payload": None}

        model = UIModel(type="EMPTY", payload={})

        # Act
        renderer.render(model, mock_callback)

        # Assert
        # 1. Verify components were drawn
        mock_hero.assert_called()
        mock_dash.assert_called()

        # 2. Verify callback
        mock_callback.assert_called_with("START_SPRINT_MANUAL", None)

        # 3. Verify rerun was triggered (standard Streamlit behavior after action)
        mock_st.rerun.assert_called()
