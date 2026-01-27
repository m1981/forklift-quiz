# ==============================================================================
# ARCHITECTURE: UNIT TEST (PRESENTATION LAYER)
# ------------------------------------------------------------------------------
# GOAL: Verify View Logic (e.g., 'If button clicked, trigger callback').
# CONSTRAINTS:
#   1. DEPENDENCIES: MUST mock the 'streamlit' library.
#   2. STATE: Verify 'st.session_state' mutations via mocks.
# ==============================================================================
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.game.core import UIModel
from src.game.steps import QuestionStepPayload, SummaryPayload, TextStepPayload
from src.quiz.domain.models import OptionKey, Question
from src.quiz.presentation.renderer import StreamlitRenderer


# ==========================================
# Class 1: General Interaction Tests
# ==========================================
class TestRendererInteractions:
    """
    Focuses on: "If I click a button, does the callback fire?"
    """

    @pytest.fixture
    def mock_streamlit(self):
        """
        Patches Streamlit at the renderer and view levels.
        """
        with patch("src.quiz.presentation.renderer.st") as mock_st:
            with patch("src.quiz.presentation.views.summary_view.st") as s_st:
                # 1. Handle Dynamic Columns (2 or 3 cols)
                def create_cols(spec=1, *args, **kwargs):
                    count = spec if isinstance(spec, int) else len(spec)
                    return [MagicMock() for _ in range(count)]

                mock_st.columns.side_effect = create_cols
                s_st.columns.side_effect = create_cols

                # --- FIX: Make session_state behave like a real dict ---
                session_state_dict = {}

                def get_item(key):
                    return session_state_dict.get(key)

                def set_item(key, value):
                    session_state_dict[key] = value

                mock_st.session_state.__getitem__.side_effect = get_item
                mock_st.session_state.__setitem__.side_effect = set_item
                # -------------------------------------------------------

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

        # Mock Payload
        mock_payload = Mock()
        mock_payload.global_progress = 0.5
        mock_payload.total_mastered = 5
        mock_payload.total_questions = 10
        mock_payload.finish_date_str = "01 Jan"
        mock_payload.days_left = 3
        mock_payload.categories = []

        model = UIModel(type="DASHBOARD", payload=mock_payload)

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

    def test_dashboard_category_action(self, renderer, mock_streamlit, mock_components):
        """
        Verifies that clicking a Category card triggers the correct callback
        and updates session state.
        """
        # Arrange
        mock_st, _ = mock_streamlit
        _, mock_dash = mock_components
        mock_callback = Mock()

        # SIMULATE USER CLICK: Category "BHP"
        mock_dash.return_value = {"type": "CATEGORY", "payload": "BHP"}

        # Mock Payload
        mock_payload = Mock()
        mock_payload.categories = []
        model = UIModel(type="DASHBOARD", payload=mock_payload)

        # Act
        renderer.render(model, mock_callback)

        # Assert
        # 1. Callback fired with correct args
        mock_callback.assert_called_with("START_CATEGORY_MANUAL", "BHP")

        # 2. Session State updated (Renderer does this side effect)
        # This assertion now works because we proxied __getitem__ to a real dict
        assert mock_st.session_state["selected_category_manual"] == "BHP"

        # 3. Rerun triggered
        mock_st.rerun.assert_called()


# ==========================================
# Class 2: Summary View Specifics
# ==========================================
class TestSummaryViewInteractions:
    """
    Targeted tests for src/quiz/presentation/views/summary_view.py
    Focus: Lines 33-34 (Finish) and 39-40 (Review)
    """

    @pytest.fixture
    def mock_dependencies(self):
        # We patch the 'st' object specifically inside the summary_view module
        with patch("src.quiz.presentation.views.summary_view.st") as mock_st:
            # 1. Handle st.columns()
            def create_cols(count):
                return [MagicMock() for _ in range(count)]

            mock_st.columns.side_effect = create_cols

            yield mock_st

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    def test_finish_button_click_triggers_callback(self, renderer, mock_dependencies):
        mock_st = mock_dependencies
        mock_callback = Mock()

        # ARRANGE
        # We simulate the user clicking the FIRST button ("Menu Główne")
        mock_st.button.side_effect = [True, False]

        payload = SummaryPayload(score=10, total=10, message="Good", has_errors=False)
        model = UIModel(type="SUMMARY", payload=payload)

        # ACT
        renderer.render(model, mock_callback)

        # ASSERT
        mock_callback.assert_called_once_with("FINISH", None)

    def test_review_button_click_triggers_callback(self, renderer, mock_dependencies):
        mock_st = mock_dependencies
        mock_callback = Mock()

        # ARRANGE
        payload = SummaryPayload(score=5, total=10, message="Bad", has_errors=True)
        model = UIModel(type="SUMMARY", payload=payload)

        # Call 1 (Menu): False, Call 2 (Review): True
        mock_st.button.side_effect = [False, True]

        # ACT
        renderer.render(model, mock_callback)

        # ASSERT
        mock_callback.assert_called_once_with("REVIEW_MISTAKES", None)

    def test_review_button_not_shown_if_no_errors(self, renderer, mock_dependencies):
        mock_st = mock_dependencies
        mock_callback = Mock()

        # ARRANGE
        payload = SummaryPayload(
            score=10, total=10, message="Perfect", has_errors=False
        )
        model = UIModel(type="SUMMARY", payload=payload)

        # ACT
        renderer.render(model, mock_callback)

        # ASSERT
        # Only one button ("Menu") should have been rendered
        assert mock_st.button.call_count == 1


# ==========================================
# Class 3: Contract Tests (Type Safety)
# ==========================================
class TestRendererContract:
    @pytest.fixture
    def mock_streamlit(self):
        """
        Patches Streamlit to prevent actual rendering during tests.
        """
        with patch("src.quiz.presentation.renderer.st") as mock_st:
            with (
                patch("src.quiz.presentation.views.question_view.st") as q_st,
                patch("src.quiz.presentation.views.summary_view.st") as s_st,
            ):
                # Mock column creation to return list of mocks
                def create_cols(spec=1, *args, **kwargs):
                    count = spec if isinstance(spec, int) else len(spec)
                    return [MagicMock() for _ in range(count)]

                mock_st.columns.side_effect = create_cols
                q_st.columns.side_effect = create_cols
                s_st.columns.side_effect = create_cols

                yield mock_st

    @pytest.fixture
    def mock_components(self):
        """
        Patches the custom mobile components (Header, Option, Result).
        """
        with patch("src.quiz.presentation.views.question_view.mobile_header") as mh:
            with patch("src.quiz.presentation.views.question_view.mobile_option") as mo:
                with patch(
                    "src.quiz.presentation.views.question_view.mobile_result_row"
                ) as mr:
                    yield mh, mo, mr

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    @pytest.fixture
    def mock_callback(self):
        return Mock()

    @pytest.mark.parametrize(
        "step_type",
        [
            "TEXT",
            "QUESTION",
            "FEEDBACK",
            "SUMMARY",
        ],
    )
    def test_renderer_supports_all_known_types(
        self, renderer, mock_callback, mock_streamlit, mock_components, step_type
    ):
        # 1. Prepare Common Data
        dummy_q = Question(
            id="Q1",
            text="Test?",
            options={OptionKey.A: "A"},
            correct_option=OptionKey.A,
            image_path=None,
            category="TestCat",
        )

        # 2. Select Payload based on Type
        if step_type == "TEXT":
            payload = TextStepPayload(
                title="T", content="C", button_text="B", image_path=None
            )

        elif step_type == "QUESTION":
            payload = QuestionStepPayload(
                question=dummy_q,
                current_index=1,
                total_count=10,
                flow_title="Test Flow",
                category_name="Test Category",
                category_mastery=0.5,
            )

        elif step_type == "FEEDBACK":
            payload = QuestionStepPayload(
                question=dummy_q,
                current_index=1,
                total_count=10,
                flow_title="Test Flow",
                category_name="Test Category",
                category_mastery=0.5,
                last_feedback={
                    "is_correct": False,
                    "selected": OptionKey.A,
                    "correct_option": OptionKey.A,
                    "explanation": "Exp",
                },
            )

        elif step_type == "SUMMARY":
            payload = SummaryPayload(score=5, total=10, message="Msg", has_errors=False)

        # 3. Act
        model = UIModel(type=step_type, payload=payload)
        renderer.render(model, mock_callback)

        # 4. Assert
        assert True
