from datetime import date
from src.quiz.domain.models import UserProfile, QuizSessionState


def test_user_profile_bonus_mode_logic():
    # Arrange
    profile = UserProfile(user_id="u1", daily_goal=3, daily_progress=3)

    # Act & Assert
    assert profile.is_bonus_mode() is True


def test_user_profile_not_in_bonus_mode():
    # Arrange
    profile = UserProfile(user_id="u1", daily_goal=3, daily_progress=2)

    # Act & Assert
    assert profile.is_bonus_mode() is False


def test_session_state_error_tracking_is_idempotent():
    """
    Adding the same error ID twice should not result in duplicates.
    """
    # Arrange
    state = QuizSessionState()

    # Act
    state.record_error("Q1")
    state.record_error("Q1")  # Duplicate
    state.record_error("Q2")

    # Assert
    assert len(state.session_error_ids) == 2
    assert "Q1" in state.session_error_ids
    assert "Q2" in state.session_error_ids


def test_session_state_resolution_removes_error():
    # Arrange
    state = QuizSessionState()
    state.record_error("Q1")

    # Act
    state.resolve_error("Q1")

    # Assert
    assert "Q1" not in state.session_error_ids


def test_session_state_mutations():
    # Arrange
    state = QuizSessionState()

    # Act: Correct Answer
    state.record_correct_answer()
    assert state.score == 1

    # Act: Next Question
    state.next_question()
    assert state.current_q_index == 1

    # Act: Reset
    state.record_error("Q1")
    state.reset(phase="Review")

    # Assert Reset
    assert state.score == 0
    assert state.current_q_index == 0
    assert len(state.session_error_ids) == 0
    assert state.internal_phase == "Review"
    assert state.is_complete is False