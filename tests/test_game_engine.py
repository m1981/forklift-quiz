import pytest
from unittest.mock import Mock, ANY
from src.game.core import GameContext, GameFlow, GameStep, UIModel
from src.game.director import GameDirector
from src.game.steps import TextStep, QuestionLoopStep
from src.quiz.domain.models import Question, OptionKey
from src.game.steps import TextStep, QuestionLoopStep, SummaryStep

# --- Mocks & Fixtures ---

@pytest.fixture
def mock_repo():
    return Mock()


@pytest.fixture
def game_context(mock_repo):
    return GameContext(user_id="TestUser", repo=mock_repo)


@pytest.fixture
def director(game_context):
    return GameDirector(game_context)


@pytest.fixture
def sample_question():
    return Question(
        id="Q1",
        text="Test?",
        options={OptionKey.A: "Yes", OptionKey.B: "No"},
        correct_option=OptionKey.A
    )


# --- 1. Testing the Director (Core Engine) ---

class TestGameDirector:

    def test_start_flow_initializes_first_step(self, director):
        # Arrange
        step1 = Mock(spec=GameStep)
        step1.get_ui_model.return_value = UIModel(type="TEST", payload={})

        mock_flow = Mock(spec=GameFlow)
        mock_flow.build_steps.return_value = [step1]

        # Act
        director.start_flow(mock_flow)

        # Assert
        assert director.get_ui_model().type == "TEST"
        step1.enter.assert_called_once()

    def test_handle_action_advances_to_next_step(self, director):
        # Arrange
        step1 = Mock(spec=GameStep)
        step1.handle_action.return_value = "NEXT"  # Signal to advance

        step2 = Mock(spec=GameStep)
        step2.get_ui_model.return_value = UIModel(type="STEP2", payload={})

        mock_flow = Mock(spec=GameFlow)
        mock_flow.build_steps.return_value = [step1, step2]

        director.start_flow(mock_flow)  # Currently on Step 1

        # Act
        director.handle_action("ANY_ACTION")

        # Assert
        # Should now be on Step 2
        assert director.get_ui_model().type == "STEP2"
        step2.enter.assert_called_once()

    def test_handle_action_dynamic_branching(self, director):
        # Arrange: Step 1 returns a NEW Step instance (Branching)
        new_step = Mock(spec=GameStep)
        new_step.get_ui_model.return_value = UIModel(type="BRANCH", payload={})

        step1 = Mock(spec=GameStep)
        step1.handle_action.return_value = new_step

        mock_flow = Mock(spec=GameFlow)
        mock_flow.build_steps.return_value = [step1]

        director.start_flow(mock_flow)

        # Act
        director.handle_action("TRIGGER_BRANCH")

        # Assert
        # Director should have inserted new_step at the front
        assert director.get_ui_model().type == "BRANCH"
        new_step.enter.assert_called_once()


# --- 2. Testing Concrete Steps (Logic Blocks) ---

class TestTextStep:
    def test_text_step_returns_correct_ui_model(self):
        step = TextStep("Title", "Content", "Btn")
        model = step.get_ui_model()

        assert model.type == "TEXT"
        assert model.payload.title == "Title"
        assert model.payload.button_text == "Btn"

    def test_text_step_next_action(self):
        step = TextStep("T", "C")
        result = step.handle_action("NEXT", None, Mock())
        assert result == "NEXT"


class TestQuestionLoopStep:

    def test_submit_correct_answer_updates_score(self, game_context, sample_question):
        # Arrange
        step = QuestionLoopStep([sample_question])
        step.enter(game_context)  # Init score=0

        # Act
        # Submit Correct Answer (A)
        result = step.handle_action("SUBMIT_ANSWER", OptionKey.A, game_context)

        # Assert
        assert game_context.data['score'] == 1
        assert result is None  # Should stay on step to show feedback

        # Check UI Model is in Feedback Mode
        model = step.get_ui_model()
        assert model.type == "FEEDBACK"
        assert model.payload.last_feedback['is_correct'] is True

    def test_submit_incorrect_answer_tracks_error(self, game_context, sample_question):
        # Arrange
        step = QuestionLoopStep([sample_question])
        step.enter(game_context)

        # Act
        # Submit Wrong Answer (B)
        step.handle_action("SUBMIT_ANSWER", OptionKey.B, game_context)

        # Assert
        assert game_context.data['score'] == 0
        assert "Q1" in game_context.data['errors']

        # Verify Repo was called to save attempt
        game_context.repo.save_attempt.assert_called_with("TestUser", "Q1", False)

    def test_next_question_advances_index(self, game_context, sample_question):
        # Arrange
        q2 = Question(id="Q2", text="?", options={}, correct_option=OptionKey.A)
        step = QuestionLoopStep([sample_question, q2])
        step.enter(game_context)

        # Act
        # 1. Submit (to enter feedback)
        step.handle_action("SUBMIT_ANSWER", OptionKey.A, game_context)
        # 2. Next
        result = step.handle_action("NEXT_QUESTION", None, game_context)

        # Assert
        assert result is None  # Stay on step because Q2 exists
        assert step.index == 1  # Moved to second question
        assert step.get_ui_model().type == "QUESTION"  # Back to Question mode (not feedback)

    def test_loop_finishes_after_last_question(self, game_context, sample_question):
        # Arrange
        step = QuestionLoopStep([sample_question])  # Only 1 question
        step.enter(game_context)

        step.handle_action("SUBMIT_ANSWER", OptionKey.A, game_context)

        # Act
        result = step.handle_action("NEXT_QUESTION", None, game_context)

        # Assert
        assert result == "NEXT"  # Signal to Director to leave this step


class TestSummaryStep:

    def test_ui_model_calculates_stats(self, game_context):
        # Arrange
        step = SummaryStep()
        game_context.data['score'] = 8
        game_context.data['total_questions'] = 10
        game_context.data['errors'] = ['Q1', 'Q2']

        step.enter(game_context)

        # Act
        model = step.get_ui_model()

        # Assert
        assert model.type == "SUMMARY"
        assert model.payload.score == 8
        assert model.payload.total == 10
        assert model.payload.has_errors is True

    def test_finish_action_returns_next(self, game_context):
        step = SummaryStep()
        step.enter(game_context)
        result = step.handle_action("FINISH", None, game_context)
        assert result == "NEXT"

    def test_review_mistakes_creates_new_loop(self, game_context):
        # Arrange
        step = SummaryStep()
        game_context.data['errors'] = ['Q1']

        # Mock repo to return a question object
        mock_q = Mock(spec=Question)
        game_context.repo.get_questions_by_ids.return_value = [mock_q]

        step.enter(game_context)

        # Act
        result = step.handle_action("REVIEW_MISTAKES", None, game_context)

        # Assert
        assert isinstance(result, QuestionLoopStep)
        assert result.questions == [mock_q]
        # Verify errors were cleared to prevent infinite loop
        assert game_context.data['errors'] == []

    def test_review_mistakes_skips_if_no_errors(self, game_context):
        # Arrange
        step = SummaryStep()
        game_context.data['errors'] = []  # No errors
        step.enter(game_context)

        # Act
        result = step.handle_action("REVIEW_MISTAKES", None, game_context)

        # Assert
        assert result == "NEXT"