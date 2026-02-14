# ==============================================================================
# ARCHITECTURE: FUNCTIONAL TEST (USER FLOWS)
# ------------------------------------------------------------------------------
# GOAL: Verify End-to-End User Scenarios via GameService.
# CONSTRAINTS:
#   1. SERVICE: Use 'src.game.service.GameService' (current architecture).
#   2. I/O: MOCKED. Use 'unittest.mock' for the Repository/Database.
# ==============================================================================
from unittest.mock import Mock, patch

import streamlit as st

from src.config import GameConfig
from src.game.service import GameService
from src.quiz.domain.models import OptionKey, Question, QuestionCandidate, UserProfile

# --- Setup Helpers ---


def create_question(id, correct_opt=OptionKey.A):
    """Helper to create a minimal valid Question object."""
    return Question(
        id=id,
        text=f"Question {id}",
        options={
            OptionKey.A: "A",
            OptionKey.B: "B",
            OptionKey.C: "C",
            OptionKey.D: "D",
        },
        correct_option=correct_opt,
        category="Test",
        explanation="Test explanation",
    )


def create_candidate(id, correct_opt=OptionKey.A, streak=0, is_seen=False):
    """Helper to create a QuestionCandidate."""
    q = create_question(id, correct_opt)
    return QuestionCandidate(question=q, streak=streak, is_seen=is_seen)


def setup_service_with_session(candidates):
    """
    Sets up a mocked GameService with session state initialized.
    Returns: (service, mock_repo)
    """
    # Mock Repository
    mock_repo = Mock()
    mock_repo.get_or_create_profile.return_value = UserProfile(user_id="TestUser")
    mock_repo.get_repetition_candidates.return_value = candidates
    mock_repo.get_category_stats.return_value = []
    mock_repo.get_mastery_percentage.return_value = 0.0
    mock_repo.save_attempt = Mock()
    mock_repo.get_questions_by_ids.return_value = [c.question for c in candidates]

    # Create Service
    service = GameService(repo=mock_repo)

    # Initialize Streamlit Session State (required by GameService)
    if not hasattr(st, "session_state"):
        st.session_state = {}

    st.session_state.clear()
    st.session_state.user_id = "TestUser"

    return service, mock_repo


# --- Tests ---


def test_daily_sprint_perfect_run():
    """
    Scenario: User starts a sprint with 3 questions and answers all correctly.
    Verifies: Flow transition, Scoring, Summary display.
    """
    # 1. Arrange
    candidates = [
        create_candidate("Q1", OptionKey.A),
        create_candidate("Q2", OptionKey.B),
        create_candidate("Q3", OptionKey.A),
    ]

    service, _ = setup_service_with_session(candidates)

    # Patch the Selector to return our exact 3 questions (deterministic)
    with patch(
        "src.quiz.domain.spaced_repetition.SpacedRepetitionSelector.select"
    ) as mock_select:
        mock_select.return_value = [c.question for c in candidates]

        # 2. Start Daily Sprint
        service.start_daily_sprint(user_id="TestUser")

        # 3. Verify Session State
        assert st.session_state.screen == "quiz"
        assert st.session_state.quiz_title == "🚀 Codzienny Sprint"
        assert len(st.session_state.quiz_questions) == 3
        assert st.session_state.current_index == 0
        assert st.session_state.score == 0

        # 4. Answer Q1 (Correct)
        q1 = st.session_state.quiz_questions[0]
        service.submit_answer("TestUser", q1, OptionKey.A)
        assert st.session_state.score == 1
        assert st.session_state.feedback_mode is True

        service.next_question()
        assert st.session_state.current_index == 1
        assert st.session_state.feedback_mode is False

        # 5. Answer Q2 (Correct)
        q2 = st.session_state.quiz_questions[1]
        service.submit_answer("TestUser", q2, OptionKey.B)
        assert st.session_state.score == 2

        service.next_question()
        assert st.session_state.current_index == 2

        # 6. Answer Q3 (Correct)
        q3 = st.session_state.quiz_questions[2]
        service.submit_answer("TestUser", q3, OptionKey.A)
        assert st.session_state.score == 3

        service.next_question()

        # 7. Verify Summary Screen
        assert st.session_state.screen == "summary"
        assert st.session_state.score == 3
        assert len(st.session_state.quiz_errors) == 0


def test_daily_sprint_with_mistakes():
    """
    Scenario: User answers 1 wrong, verifies error tracking.
    """
    # 1. Arrange
    candidates = [
        create_candidate("Q1", OptionKey.A),
        create_candidate("Q2", OptionKey.B),
    ]

    service, mock_repo = setup_service_with_session(candidates)

    with patch(
        "src.quiz.domain.spaced_repetition.SpacedRepetitionSelector.select"
    ) as mock_select:
        mock_select.return_value = [c.question for c in candidates]

        # 2. Start
        service.start_daily_sprint(user_id="TestUser")

        # 3. Answer Q1 (WRONG)
        q1 = st.session_state.quiz_questions[0]
        service.submit_answer("TestUser", q1, OptionKey.B)  # Wrong answer

        assert st.session_state.score == 0
        assert "Q1" in st.session_state.quiz_errors
        assert st.session_state.last_feedback["is_correct"] is False

        service.next_question()

        # 4. Answer Q2 (Correct)
        q2 = st.session_state.quiz_questions[1]
        service.submit_answer("TestUser", q2, OptionKey.B)

        assert st.session_state.score == 1

        service.next_question()

        # 5. Verify Summary
        assert st.session_state.screen == "summary"
        assert st.session_state.score == 1
        assert len(st.session_state.quiz_errors) == 1


def test_category_mode_selection():
    """
    Scenario: User starts Category Mode with specific category.
    """
    # 1. Arrange
    mock_repo = Mock()
    mock_repo.get_or_create_profile.return_value = UserProfile(user_id="TestUser")

    category_questions = [create_question(f"Q{i}", OptionKey.A) for i in range(5)]
    mock_repo.get_questions_by_category.return_value = category_questions

    service = GameService(repo=mock_repo)

    if not hasattr(st, "session_state"):
        st.session_state = {}
    st.session_state.clear()

    # 2. Start Category Mode
    service.start_category_mode(user_id="TestUser", category="BHP")

    # 3. Verify
    assert st.session_state.screen == "quiz"
    assert st.session_state.quiz_title == "📚 BHP"
    assert len(st.session_state.quiz_questions) == 5

    mock_repo.get_questions_by_category.assert_called_once_with(
        "BHP", "TestUser", limit=GameConfig.SPRINT_QUESTIONS
    )


def test_onboarding_flow():
    """
    Scenario: New user completes onboarding.
    """
    # 1. Arrange
    mock_repo = Mock()
    profile = UserProfile(user_id="NewUser", has_completed_onboarding=False)
    mock_repo.get_or_create_profile.return_value = profile
    mock_repo.save_profile = Mock()

    service = GameService(repo=mock_repo)

    if not hasattr(st, "session_state"):
        st.session_state = {}
    st.session_state.clear()

    # 2. Start Onboarding
    service.start_onboarding(user_id="NewUser")

    # 3. Verify
    assert st.session_state.screen == "quiz"
    assert st.session_state.quiz_title == "🎓 Szkolenie Wstępne"
    assert len(st.session_state.quiz_questions) == 1
    assert st.session_state.quiz_questions[0].id == "TUT-01"

    # Verify profile was updated
    mock_repo.save_profile.assert_called_once()
    saved_profile = mock_repo.save_profile.call_args[0][0]
    assert saved_profile.has_completed_onboarding is True
