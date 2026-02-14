from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from src.quiz.domain.models import Language, UserProfile
from src.quiz.domain.profile_manager import ProfileManager


@pytest.fixture
def mock_repo():
    repo = Mock()
    repo.get_or_create_profile.return_value = UserProfile(
        user_id="test_user",
        streak_days=5,
        last_login=date.today(),
        daily_progress=2,
        last_daily_reset=date.today(),
    )
    repo.save_profile = Mock()
    return repo


def test_profile_cached_after_first_fetch(mock_repo):
    """Profile should only be fetched once per session."""
    manager = ProfileManager(mock_repo, "test_user")

    # First call fetches from DB
    profile1 = manager.get()
    assert mock_repo.get_or_create_profile.call_count == 1

    # Second call uses cache
    profile2 = manager.get()
    assert mock_repo.get_or_create_profile.call_count == 1
    assert profile1 is profile2


def test_daily_progress_resets_at_midnight(mock_repo):
    """Daily progress should reset when date changes."""
    yesterday = date.today() - timedelta(days=1)

    profile = UserProfile(
        user_id="test_user",
        daily_progress=10,
        last_daily_reset=yesterday,
    )
    mock_repo.get_or_create_profile.return_value = profile

    manager = ProfileManager(mock_repo, "test_user")
    manager.increment_daily_progress()

    # Should reset to 0, then increment to 1
    assert profile.daily_progress == 1
    assert profile.last_daily_reset == date.today()

    # Date change is critical - should save immediately
    assert mock_repo.save_profile.call_count == 1


def test_language_update_marks_dirty(mock_repo):
    """Changing language should trigger immediate save."""
    manager = ProfileManager(mock_repo, "test_user")

    manager.update_language(Language.EN)

    # Should save immediately
    assert mock_repo.save_profile.call_count == 1
    profile = manager.get()
    assert profile.preferred_language == Language.EN


def test_flush_batches_updates(mock_repo):
    """Multiple changes should be batched, then flushed."""
    # Start with daily_progress = 2, TODAY (no date reset)
    profile = UserProfile(
        user_id="test_user",
        daily_progress=2,
        last_daily_reset=date.today(),  # Same day!
    )
    mock_repo.get_or_create_profile.return_value = profile

    manager = ProfileManager(mock_repo, "test_user")

    # Make 3 increments (should batch them, not save yet)
    manager.increment_daily_progress()  # 2 -> 3
    manager.increment_daily_progress()  # 3 -> 4
    manager.increment_daily_progress()  # 4 -> 5

    # Should NOT have saved yet (threshold is 5 changes, we made 3)
    assert mock_repo.save_profile.call_count == 0

    # Verify the profile was updated in memory
    profile = manager.get()
    assert profile.daily_progress == 5

    # Now explicitly flush to save
    manager.flush()

    # Should have saved once
    assert mock_repo.save_profile.call_count == 1


def test_increment_saves_every_5th_change(mock_repo):
    """ProfileManager should auto-save every 5 changes."""
    profile = UserProfile(
        user_id="test_user",
        daily_progress=0,
        last_daily_reset=date.today(),
    )
    mock_repo.get_or_create_profile.return_value = profile

    manager = ProfileManager(mock_repo, "test_user")

    # Make 4 increments (should NOT save yet)
    for _ in range(4):
        manager.increment_daily_progress()

    assert mock_repo.save_profile.call_count == 0

    # 5th increment should trigger auto-save
    manager.increment_daily_progress()

    assert mock_repo.save_profile.call_count == 1
    assert profile.daily_progress == 5


def test_complete_onboarding_saves_immediately(mock_repo):
    """Critical changes like onboarding should save immediately."""
    profile = UserProfile(
        user_id="test_user",
        has_completed_onboarding=False,
    )
    mock_repo.get_or_create_profile.return_value = profile

    manager = ProfileManager(mock_repo, "test_user")
    manager.complete_onboarding()

    assert profile.has_completed_onboarding is True
    assert mock_repo.save_profile.call_count == 1


def test_date_reset_happens_before_increment(mock_repo):
    """When date changes, reset should happen BEFORE incrementing."""
    yesterday = date.today() - timedelta(days=1)

    profile = UserProfile(
        user_id="test_user",
        daily_progress=10,
        last_daily_reset=yesterday,
    )
    mock_repo.get_or_create_profile.return_value = profile

    manager = ProfileManager(mock_repo, "test_user")

    # First increment on new day
    manager.increment_daily_progress()

    # Should be 1 (reset to 0, then incremented)
    assert profile.daily_progress == 1
    assert profile.last_daily_reset == date.today()

    # Second increment same day
    manager.increment_daily_progress()

    # Should be 2 (no reset)
    assert profile.daily_progress == 2
    assert profile.last_daily_reset == date.today()
