# ==============================================================================
# ARCHITECTURE: UNIT TEST (CORE LOGIC)
# ------------------------------------------------------------------------------
# GOAL: Verify pure business logic, state transitions, and algorithms.
# CONSTRAINTS:
#   1. EXECUTION: FAST (< 50ms per test).
#   2. I/O: FORBIDDEN. No Database, No Network, No File System.
#   3. MOCKS: Mandatory for Repositories and External Services.
# ==============================================================================
from src.quiz.domain.models import UserProfile


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
