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

from src.game.service import GameService
from src.quiz.domain.models import OptionKey, Question, QuestionCandidate, UserProfile

# --- Setup Helpers ---


def create_question(id, correct_opt=OptionKey.A):
    """Helper to create a Question object."""
    return Question(
        id=id,
        text=f"Question {id}?",
        options={
            OptionKey.A: "Option A",
            OptionKey.B: "Option B",
            OptionKey.C: "Option C",
            OptionKey.D: "Option D",
        },
        correct_option=correct_opt,
        category="Test",
        explanation="Test explanation",
    )


def create_candidate(id, correct_opt=OptionKey.A, streak=0, is_seen=False):
    """Helper to create a QuestionCandidate (wrapper around Question)."""
    question = create_question(id, correct_opt)
    return QuestionCandidate(
        question=question,
        streak=streak,
        is_seen=is_seen,
    )


def setup_service(candidates):
    """Helper to create service with mocked repo and initialized session."""
    mock_repo = Mock()
    mock_repo.get_repetition_candidates.return_value = candidates
    mock_repo.get_or_create_profile.return_value = UserProfile(
        user_id="test_user",
        has_completed_onboarding=True,
    )
    mock_repo.save_attempt = Mock()
    mock_repo.save_profile = Mock()

    # Initialize session state (required by GameService)
    if not hasattr(st, "session_state"):
        st.session_state = {}
    st.session_state.clear()

    service = GameService(mock_repo, user_id="test_user")
    return service, mock_repo


# --- Tests ---


def test_daily_sprint_perfect_run():
    """User answers all questions correctly."""
    candidates = [
        create_candidate("Q1", OptionKey.A),
        create_candidate("Q2", OptionKey.B),
        create_candidate("Q3", OptionKey.A),
    ]

    service, mock_repo = setup_service(candidates)

    # Mock the selector to return our exact questions
    with patch(
        "src.quiz.domain.spaced_repetition.SpacedRepetitionSelector.select"
    ) as mock_select:
        mock_select.return_value = [c.question for c in candidates]

        # Start sprint
        service.start_daily_sprint("test_user")

        # Verify session state initialized
        assert st.session_state.screen == "quiz"
        assert st.session_state.quiz_title == "🚀 Codzienny Sprint"
        assert len(st.session_state.quiz_questions) == 3
        assert st.session_state.current_index == 0
        assert st.session_state.score == 0

        # Answer Q1 correctly
        q1 = st.session_state.quiz_questions[0]
        service.submit_answer("test_user", q1, OptionKey.A)
        assert st.session_state.score == 1
        assert st.session_state.feedback_mode is True

        service.next_question()
        assert st.session_state.current_index == 1
        assert st.session_state.feedback_mode is False

        # Answer Q2 correctly
        q2 = st.session_state.quiz_questions[1]
        service.submit_answer("test_user", q2, OptionKey.B)
        assert st.session_state.score == 2

        service.next_question()
        assert st.session_state.current_index == 2

        # Answer Q3 correctly
        q3 = st.session_state.quiz_questions[2]
        service.submit_answer("test_user", q3, OptionKey.A)
        assert st.session_state.score == 3

        service.next_question()

        # Verify summary screen
        assert st.session_state.screen == "summary"
        assert st.session_state.score == 3
        assert len(st.session_state.quiz_errors) == 0


def test_daily_sprint_with_mistakes():
    """User makes mistakes and they are tracked."""
    candidates = [
        create_candidate("Q1", OptionKey.A),
        create_candidate("Q2", OptionKey.B),
        create_candidate("Q3", OptionKey.A),
    ]

    service, mock_repo = setup_service(candidates)

    with patch(
        "src.quiz.domain.spaced_repetition.SpacedRepetitionSelector.select"
    ) as mock_select:
        mock_select.return_value = [c.question for c in candidates]

        service.start_daily_sprint("test_user")

        # Answer Q1 WRONG
        q1 = st.session_state.quiz_questions[0]
        service.submit_answer("test_user", q1, OptionKey.B)  # Wrong!

        assert st.session_state.score == 0
        assert "Q1" in st.session_state.quiz_errors
        assert st.session_state.last_feedback["is_correct"] is False

        service.next_question()

        # Answer Q2 correctly
        q2 = st.session_state.quiz_questions[1]
        service.submit_answer("test_user", q2, OptionKey.B)
        assert st.session_state.score == 1

        service.next_question()

        # Answer Q3 correctly
        q3 = st.session_state.quiz_questions[2]
        service.submit_answer("test_user", q3, OptionKey.A)
        assert st.session_state.score == 2

        service.next_question()

        # Verify summary
        assert st.session_state.screen == "summary"
        assert st.session_state.score == 2
        assert len(st.session_state.quiz_errors) == 1


def test_category_mode_selection():
    """User selects specific category."""
    mock_repo = Mock()

    # Create actual Question objects (not candidates)
    questions = [create_question(f"Q{i}", OptionKey.A) for i in range(5)]

    mock_repo.get_questions_by_category.return_value = questions
    mock_repo.get_or_create_profile.return_value = UserProfile(
        user_id="test_user",
        has_completed_onboarding=True,
    )

    # Initialize session state
    if not hasattr(st, "session_state"):
        st.session_state = {}
    st.session_state.clear()

    service = GameService(mock_repo, user_id="test_user")
    service.start_category_mode("test_user", "BHP")

    # Verify
    assert st.session_state.screen == "quiz"
    assert st.session_state.quiz_title == "📚 BHP"
    assert len(st.session_state.quiz_questions) == 5

    mock_repo.get_questions_by_category.assert_called_once()


def test_onboarding_flow():
    """New user completes onboarding."""
    mock_repo = Mock()
    mock_repo.get_or_create_profile.return_value = UserProfile(
        user_id="new_user",
        has_completed_onboarding=False,
    )
    mock_repo.save_profile = Mock()

    # Initialize session state
    if not hasattr(st, "session_state"):
        st.session_state = {}
    st.session_state.clear()

    service = GameService(mock_repo, user_id="new_user")
    service.start_onboarding("new_user")

    # Verify
    assert st.session_state.screen == "quiz"
    assert st.session_state.quiz_title == "🎓 Szkolenie Wstępne"
    assert len(st.session_state.quiz_questions) == 1
    assert st.session_state.quiz_questions[0].id == "TUT-01"

    # Profile should be marked as onboarded
    mock_repo.save_profile.assert_called_once()
    saved_profile = mock_repo.save_profile.call_args[0][0]
    assert saved_profile.has_completed_onboarding is True
