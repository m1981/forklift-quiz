import pytest
import sqlite3
from datetime import date, timedelta
from src.repository import SQLiteQuizRepository
from src.models import UserProfile


# --- Fixtures ---
@pytest.fixture
def repo():
    """Creates an isolated in-memory repository for each test."""
    return SQLiteQuizRepository(db_path=":memory:")


# --- Tests for get_or_create_profile ---

def test_create_new_profile(repo):
    """
    Scenario: User logs in for the very first time.
    Expected: A new profile is created with default values (streak=0, progress=0).
    """
    user_id = "NewUser"
    profile = repo.get_or_create_profile(user_id)

    assert profile.user_id == user_id
    assert profile.streak_days == 0
    assert profile.daily_progress == 0
    assert profile.last_login == date.today()


def test_get_existing_profile(repo):
    """
    Scenario: User logs in again on the same day.
    Expected: Returns the existing profile without resetting anything.
    """
    user_id = "ExistingUser"

    # 1. Create initial profile manually in DB to simulate state
    with repo._get_connection() as conn:
        conn.execute("""
                     INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress,
                                                last_daily_reset)
                     VALUES (?, 5, ?, 10, 3, ?)
                     """, (user_id, date.today(), date.today()))

    # 2. Fetch via method
    profile = repo.get_or_create_profile(user_id)

    assert profile.streak_days == 5
    assert profile.daily_progress == 3


def test_daily_reset_logic(repo):
    """
    Scenario: User logs in the next day (or later).
    Expected: Daily progress resets to 0, but streak remains (until updated).
    """
    user_id = "ReturningUser"
    yesterday = date.today() - timedelta(days=1)

    # 1. Simulate a user who did 8 questions yesterday
    with repo._get_connection() as conn:
        conn.execute("""
                     INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress,
                                                last_daily_reset)
                     VALUES (?, 5, ?, 10, 8, ?)
                     """, (user_id, yesterday, yesterday))

    # 2. Fetch today
    profile = repo.get_or_create_profile(user_id)

    # 3. Assertions
    assert profile.daily_progress == 0  # Should be reset!
    assert profile.last_daily_reset == date.today()  # Should be updated to today
    assert profile.streak_days == 5  # Streak hasn't changed yet (only changes on action)


# --- Tests for update_profile_stats ---

def test_streak_increment_consecutive_days(repo):
    """
    Scenario: User logged in yesterday and answers a question today.
    Expected: Streak increases by 1.
    """
    user_id = "StreakUser"
    yesterday = date.today() - timedelta(days=1)

    # 1. Setup: Last login yesterday, streak 5
    with repo._get_connection() as conn:
        conn.execute("""
                     INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress,
                                                last_daily_reset)
                     VALUES (?, 5, ?, 10, 0, ?)
                     """,
                     (user_id, yesterday, date.today()))  # Note: last_daily_reset is today (handled by get_or_create)

    # 2. Action: User answers a question
    repo.update_profile_stats(user_id)

    # 3. Verify
    profile = repo.get_or_create_profile(user_id)
    assert profile.streak_days == 6
    assert profile.last_login == date.today()
    assert profile.daily_progress == 1


def test_streak_reset_missed_day(repo):
    """
    Scenario: User missed a day (last login 2 days ago).
    Expected: Streak resets to 1 (starting over today).
    """
    user_id = "LazyUser"
    two_days_ago = date.today() - timedelta(days=2)

    # 1. Setup: Last login 2 days ago, streak was 10
    with repo._get_connection() as conn:
        conn.execute("""
                     INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress,
                                                last_daily_reset)
                     VALUES (?, 10, ?, 10, 0, ?)
                     """, (user_id, two_days_ago, date.today()))

    # 2. Action
    repo.update_profile_stats(user_id)

    # 3. Verify
    profile = repo.get_or_create_profile(user_id)
    assert profile.streak_days == 1  # Reset!
    assert profile.daily_progress == 1


def test_same_day_activity_does_not_increase_streak(repo):
    """
    Scenario: User answers multiple questions on the same day.
    Expected: Streak stays same, daily progress increases.
    """
    user_id = "ActiveUser"

    # 1. Setup: Logged in today already
    with repo._get_connection() as conn:
        conn.execute("""
                     INSERT INTO user_profiles (user_id, streak_days, last_login, daily_goal, daily_progress,
                                                last_daily_reset)
                     VALUES (?, 5, ?, 10, 2, ?)
                     """, (user_id, date.today(), date.today()))

    # 2. Action
    repo.update_profile_stats(user_id)

    # 3. Verify
    profile = repo.get_or_create_profile(user_id)
    assert profile.streak_days == 5  # Unchanged
    assert profile.daily_progress == 3  # Increased