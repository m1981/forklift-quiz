import pytest
from unittest.mock import Mock, patch
from src.game.core import UIModel
from src.quiz.presentation.renderer import StreamlitRenderer
from src.game.steps import TextStepPayload, QuestionStepPayload, SummaryPayload
from src.quiz.domain.models import Question, OptionKey


class TestRendererContract:
    """
    Ensures the Renderer handles ALL possible UIModel types produced by the Engine.
    """

    @pytest.fixture
    def mock_streamlit(self):
        """
        Patches streamlit so we don't actually render to a browser.
        Crucially, we must configure st.columns to return a list of mocks.
        """
        with patch('src.quiz.presentation.renderer.st') as mock_st_renderer, \
                patch('src.quiz.presentation.views.question_view.st') as mock_st_q, \
                patch('src.quiz.presentation.views.summary_view.st') as mock_st_s, \
                patch('src.quiz.presentation.views.question_view.os.path.exists') as mock_exists:
            # 1. Fix Image Loading
            mock_exists.return_value = False

            # 2. Fix st.columns unpacking
            # We define a side_effect that returns N mocks based on the input integer
            def columns_side_effect(count):
                return [Mock() for _ in range(count)]

            mock_st_q.columns.side_effect = columns_side_effect
            mock_st_s.columns.side_effect = columns_side_effect

            yield mock_st_renderer

    @pytest.fixture
    def renderer(self):
        return StreamlitRenderer()

    @pytest.fixture
    def mock_callback(self):
        return Mock()

    def test_renderer_handles_loading_state(self, renderer, mock_callback, mock_streamlit):
        model = UIModel(type="LOADING", payload={})
        renderer.render(model, mock_callback)
        mock_streamlit.info.assert_called()

    def test_renderer_handles_empty_state(self, renderer, mock_callback, mock_streamlit):
        model = UIModel(type="EMPTY", payload={"message": "Done"})
        renderer.render(model, mock_callback)
        mock_streamlit.info.assert_called()

    @pytest.mark.parametrize("step_type", [
        "TEXT",
        "QUESTION",
        "FEEDBACK",
        "SUMMARY",
    ])
    def test_renderer_supports_all_known_types(self, renderer, mock_callback, mock_streamlit, step_type):
        """
        We construct REAL payloads here to ensure the views don't crash
        on type errors (like int vs mock comparisons).
        """

        # 1. Prepare Common Data
        dummy_q = Question(
            id="Q1",
            text="Test?",
            options={OptionKey.A: "A"},
            correct_option=OptionKey.A,
            image_path=None
        )

        # 2. Select Payload based on Type
        if step_type == "TEXT":
            payload = TextStepPayload(title="T", content="C", button_text="B", image_path=None)

        elif step_type == "QUESTION":
            payload = QuestionStepPayload(
                question=dummy_q,
                current_index=1,
                total_count=10
            )

        elif step_type == "FEEDBACK":
            payload = QuestionStepPayload(
                question=dummy_q,
                current_index=1,
                total_count=10,
                last_feedback={
                    'is_correct': False,
                    'selected': OptionKey.A,
                    'correct_option': OptionKey.A,
                    'explanation': "Exp"
                }
            )

        elif step_type == "SUMMARY":
            payload = SummaryPayload(score=5, total=10, message="Msg")

        else:
            payload = {}

        # 3. Execute Render
        model = UIModel(type=step_type, payload=payload)

        try:
            renderer.render(model, mock_callback)
        except Exception as e:
            pytest.fail(f"Renderer crashed on valid {step_type} payload: {e}")