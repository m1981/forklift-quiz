import pytest
from datetime import date
from src.repository import SQLiteQuizRepository
from src.service import QuizService
from src.models import Question, OptionKey, UserProfile


# --- Fixtures ---
@pytest.fixture
def service():
    # Use in-memory DB for isolation and speed
    repo = SQLiteQuizRepository(db_path=":memory:")
    svc = QuizService(repo)
    return svc


@pytest.fixture
def sample_question_1():
    return Question(
        id="Q1",
        text="Test Q1",
        options={OptionKey.A: "A", OptionKey.B: "B"},
        correct_option=OptionKey.A
    )


@pytest.fixture
def sample_question_2():
    return Question(
        id="Q2",
        text="Test Q2",
        options={OptionKey.A: "A", OptionKey.B: "B"},
        correct_option=OptionKey.B
    )


# --- TDD Test Cases ---

def test_daily_progress_increments_on_new_question(service, sample_question_1):
    """
    Happy Path: Answering a new question should increment progress.
    """
    user_id = "Tester"

    # Act
    service.submit_answer(user_id, sample_question_1, OptionKey.A)

    # Assert
    profile = service.get_user_profile(user_id)
    assert profile.daily_progress == 1, "Progress should be 1 after first question"


def test_daily_progress_ignores_repetitions_same_day(service, sample_question_1):
    """
    THE BUG REPRODUCER: Answering the SAME question twice in one day
    should NOT increment the counter the second time.
    """
    user_id = "Farmer"

    # 1. First Attempt (Should Count)
    service.submit_answer(user_id, sample_question_1, OptionKey.A)
    profile_after_first = service.get_user_profile(user_id)
    assert profile_after_first.daily_progress == 1

    # 2. Second Attempt - Same Question, Same Day (Should NOT Count)
    service.submit_answer(user_id, sample_question_1, OptionKey.A)
    profile_after_second = service.get_user_profile(user_id)

    # This assertion will FAIL if the bug exists (it will be 2)
    assert profile_after_second.daily_progress == 1, \
        f"Progress should remain 1. Found {profile_after_second.daily_progress}. Repetitions are being counted!"


def test_daily_progress_counts_different_questions(service, sample_question_1, sample_question_2):
    """
    Ensure we can still advance by answering DIFFERENT questions.
    """
    user_id = "Learner"

    # Q1
    service.submit_answer(user_id, sample_question_1, OptionKey.A)
    # Q2
    service.submit_answer(user_id, sample_question_2, OptionKey.B)

    profile = service.get_user_profile(user_id)
    assert profile.daily_progress == 2, "Progress should be 2 after answering two DIFFERENT questions"