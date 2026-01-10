import pytest
from unittest.mock import MagicMock, patch
from src.viewmodel import QuizViewModel
from src.models import Question, OptionKey, UserProfile


# --- Helper Class for Mocking Session State ---
class MockSessionState(dict):
    """
    A dictionary that allows attribute access (dot notation)
    to mimic Streamlit's session_state behavior.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value


# --- Fixtures ---

@pytest.fixture
def mock_service():
    service = MagicMock()
    # Default Profile
    service.get_user_profile.return_value = UserProfile(user_id="TestUser", daily_progress=5, daily_goal=10)
    # Default Questions
    q1 = Question(id="1", text="Q1", options={"A": "A"}, correct_option="A", explanation="Exp")
    q2 = Question(id="2", text="Q2", options={"B": "B"}, correct_option="B", explanation="Exp")
    service.get_quiz_questions.return_value = [q1, q2]
    return service


@pytest.fixture
def mock_session_state():
    """
    Patches streamlit.session_state with our custom MockSessionState class.
    """
    # We use our custom class instead of a plain dict
    mock_state = MockSessionState()

    with patch("src.viewmodel.st.session_state", mock_state):
        yield mock_state


# --- Tests ---

def test_load_quiz_initializes_state(mock_service, mock_session_state):
    vm = QuizViewModel(mock_service)

    # Action
    vm.load_quiz("Standard", "TestUser")

    # Assertions (Dot notation now works on the mock)
    assert len(mock_session_state.quiz_questions) == 2
    assert mock_session_state.current_index == 0
    assert mock_session_state.score == 0
    assert mock_session_state.user_profile.daily_progress == 5
    assert mock_session_state.quiz_complete is False


def test_submit_answer_updates_score_and_syncs_profile(mock_service, mock_session_state):
    vm = QuizViewModel(mock_service)
    vm.load_quiz("Standard", "TestUser")

    # Setup: Service returns True for correct answer
    mock_service.submit_answer.return_value = True

    # Setup: Service returns UPDATED profile after answer (Progress 5 -> 6)
    updated_profile = UserProfile(user_id="TestUser", daily_progress=6, daily_goal=10)
    mock_service.get_user_profile.return_value = updated_profile

    # Action: Submit Correct Answer for Q1 (Option A)
    vm.submit_answer("TestUser", OptionKey.A)

    # Assertions
    assert mock_session_state.score == 1
    assert mock_session_state.answer_submitted is True
    assert mock_session_state.last_feedback['type'] == 'success'

    # CRITICAL: Profile must be updated in session state
    assert mock_session_state.user_profile.daily_progress == 6


def test_submit_last_answer_triggers_completion(mock_service, mock_session_state):
    vm = QuizViewModel(mock_service)
    vm.load_quiz("Standard", "TestUser")

    # Move to last question (Index 1, since len is 2)
    mock_session_state.current_index = 1

    # Action: Submit Answer
    vm.submit_answer("TestUser", OptionKey.B)

    # Assertions
    assert mock_session_state.quiz_complete is True