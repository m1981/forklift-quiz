from unittest.mock import MagicMock, Mock, patch

import pytest

from src.game.core import UIModel
from src.game.steps import QuestionStepPayload, SummaryPayload, TextStepPayload
from src.quiz.domain.models import OptionKey, Question
from src.quiz.presentation.renderer import StreamlitRenderer


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
                # FIX: Added missing fields required by the new Header
                flow_title="Test Flow",
                category_name="Test Category",
                category_mastery=0.5,
            )

        elif step_type == "FEEDBACK":
            payload = QuestionStepPayload(
                question=dummy_q,
                current_index=1,
                total_count=10,
                # FIX: Added missing fields
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
        # If we reached here without an exception, the contract is valid.
        assert True
