import pytest
from datetime import date, timedelta
from src.quiz.domain.models import Question, OptionKey


def test_seed_and_retrieve_questions(in_memory_repo, sample_question):
    # Arrange
    questions = [sample_question]

    # Act
    in_memory_repo.seed_questions(questions)
    retrieved = in_memory_repo.get_all_questions()

    # Assert
    assert len(retrieved) == 1
    assert retrieved[0].id == sample_question.id
    assert retrieved[0].text == sample_question.text


def test_get_questions_by_ids(populated_repo, sample_question):
    # Arrange
    # Add a second question to ensure filtering works
    q2 = Question(
        id="Q2", text="B?", options={}, correct_option=OptionKey.A
    )
    populated_repo.seed_questions([q2])

    # Act
    # We only want Q1
    results = populated_repo.get_questions_by_ids(["Q1"])

    # Assert
    assert len(results) == 1
    assert results[0].id == "Q1"


def test_user_profile_creation_persistence(in_memory_repo, sample_user_id):
    # Arrange
    # First call creates it
    profile = in_memory_repo.get_or_create_profile(sample_user_id)
    assert profile.streak_days == 0

    # Act
    profile.streak_days = 5
    in_memory_repo.save_profile(profile)

    # Assert
    # Second call retrieves it
    updated_profile = in_memory_repo.get_or_create_profile(sample_user_id)
    assert updated_profile.streak_days == 5


def test_save_attempt_updates_history(populated_repo, sample_user_id):
    # Arrange
    q_id = "Q1"

    # Act
    populated_repo.save_attempt(sample_user_id, q_id, is_correct=False)

    # Assert
    incorrect_ids = populated_repo.get_incorrect_question_ids(sample_user_id)
    assert q_id in incorrect_ids

    # Act 2: Correct the mistake
    populated_repo.save_attempt(sample_user_id, q_id, is_correct=True)

    # Assert 2
    incorrect_ids_after = populated_repo.get_incorrect_question_ids(sample_user_id)
    assert q_id not in incorrect_ids_after


def test_was_question_answered_on_specific_date(populated_repo, sample_user_id):
    """
    This tests the fix we made to remove 'date(now)' from SQL.
    We inject specific dates to ensure time-travel testing works.
    """
    # Arrange
    q_id = "Q1"
    today = date(2023, 1, 1)
    yesterday = date(2022, 12, 31)

    # Act: Save attempt (Note: The repo defaults to CURRENT_TIMESTAMP in SQL,
    # so strictly speaking, this test relies on the system clock for the INSERT.
    # However, our 'was_question_answered_on_date' check filters by the date passed in.
    # To truly test this without system clock dependency, we'd need to pass the timestamp
    # into save_attempt too. For now, we assume the test runs 'today'.)

    populated_repo.save_attempt(sample_user_id, q_id, is_correct=True)

    # Assert
    real_today = date.today()
    assert populated_repo.was_question_answered_on_date(sample_user_id, q_id, real_today) is True

    # It should NOT show as answered yesterday
    assert populated_repo.was_question_answered_on_date(sample_user_id, q_id, yesterday) is False


def test_reset_progress_wipes_data(populated_repo, sample_user_id):
    # Arrange
    populated_repo.save_attempt(sample_user_id, "Q1", True)
    profile = populated_repo.get_or_create_profile(sample_user_id)
    profile.streak_days = 10
    populated_repo.save_profile(profile)

    # Act
    populated_repo.reset_user_progress(sample_user_id)

    # Assert
    attempts = populated_repo.get_all_attempted_ids(sample_user_id)
    assert len(attempts) == 0

    new_profile = populated_repo.get_or_create_profile(sample_user_id)
    assert new_profile.streak_days == 0