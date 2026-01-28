# tests/integration/repository/test_streak_persistence.py

from datetime import date, timedelta

import pytest

from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository

# --- Fixtures ---


@pytest.fixture
def repo():
    db = DatabaseManager(":memory:")
    repo = SQLiteQuizRepository(db)
    yield repo
    # Cleanup: Close the database connection
    db.close()


@pytest.fixture
def user_id():
    return "StreakUser"


# --- Tests ---


def test_new_user_starts_with_streak_one(repo, user_id):
    """
    GIVEN a user who has never logged in
    WHEN get_or_create_profile is called
    THEN the streak should be 1
    """
    profile = repo.get_or_create_profile(user_id)

    assert profile.streak_days == 1
    assert profile.last_login == date.today()


def test_consecutive_login_increments_streak(repo, user_id):
    """
    GIVEN a user who logged in yesterday with streak 5
    WHEN they log in today
    THEN the streak should become 6
    """
    # 1. Setup: Create a profile "in the past"
    today = date.today()
    yesterday = today - timedelta(days=1)

    # Manually insert a profile representing "Yesterday"
    # We bypass the public API to set up the exact state we want (White Box Testing)
    conn = repo._get_connection()
    conn.execute(
        """
        INSERT INTO user_profiles (user_id, streak_days, last_login)
        VALUES (?, ?, ?)
        """,
        # FIX: Use .isoformat() for date
        (user_id, 5, yesterday.isoformat()),
    )
    conn.commit()

    # 2. Action: Log in "Today"
    profile = repo.get_or_create_profile(user_id)

    # 3. Assertion
    assert profile.streak_days == 6
    assert profile.last_login == today


def test_missed_day_resets_streak(repo, user_id):
    """
    GIVEN a user who logged in 2 days ago (missed yesterday)
    WHEN they log in today
    THEN the streak should reset to 1
    """
    today = date.today()
    two_days_ago = today - timedelta(days=2)

    # Setup: User had a massive streak of 100, but missed a day
    conn = repo._get_connection()
    conn.execute(
        """
        INSERT INTO user_profiles (user_id, streak_days, last_login)
        VALUES (?, ?, ?)
        """,
        # FIX: Use .isoformat() for date
        (user_id, 100, two_days_ago.isoformat()),
    )
    conn.commit()

    # Action
    profile = repo.get_or_create_profile(user_id)

    # Assertion: Sudden Death
    assert profile.streak_days == 1
    assert profile.last_login == today


def test_same_day_login_does_not_increment(repo, user_id):
    """
    GIVEN a user who already logged in today
    WHEN they log in again (e.g., refresh page)
    THEN the streak should NOT increment
    """
    # 1. First Login
    profile_1 = repo.get_or_create_profile(user_id)
    assert profile_1.streak_days == 1

    # 2. Second Login (Same Day)
    profile_2 = repo.get_or_create_profile(user_id)

    # Assertion
    assert profile_2.streak_days == 1  # Should still be 1, not 2
    assert profile_2.last_login == date.today()


def test_future_date_correction(repo, user_id):
    """
    Corner Case: System clock skew.
    GIVEN a user with a last_login in the future (e.g. clock error previously)
    WHEN they log in 'today' (which is technically 'before' the DB date)
    THEN the logic should treat it as a reset (delta is negative or handled as non-1)
    """
    today = date.today()
    tomorrow = today + timedelta(days=1)

    conn = repo._get_connection()
    conn.execute(
        """
        INSERT INTO user_profiles (user_id, streak_days, last_login)
        VALUES (?, ?, ?)
        """,
        # FIX: Use .isoformat() for date
        (user_id, 10, tomorrow.isoformat()),
    )
    conn.commit()

    profile = repo.get_or_create_profile(user_id)

    # Our logic: delta = today - tomorrow = -1.
    # The `elif delta == 1` check fails.
    # The `else` block executes.
    # Streak resets. This is the safe fallback behavior.
    assert profile.streak_days == 1
    assert profile.last_login == today
