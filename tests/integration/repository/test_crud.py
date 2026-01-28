# ==============================================================================
# ARCHITECTURE: INTEGRATION TEST (ADAPTER LAYER)
# ------------------------------------------------------------------------------
# GOAL: Verify Data Persistence and SQL Logic.
# CONSTRAINTS:
#   1. DATABASE: Use a real SQLite instance (In-Memory or Temp File).
#   2. SCOPE: Test CRUD operations, Complex Queries, and Data Integrity.
# ==============================================================================
import pytest

from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.domain.models import OptionKey, Question


# --- Fixtures (Assumed from context, added here for completeness) ---
@pytest.fixture
def in_memory_repo():
    db = DatabaseManager(":memory:")
    return SQLiteQuizRepository(db)


@pytest.fixture
def sample_question():
    return Question(
        id="Q1", text="T", options={OptionKey.A: "A"}, correct_option=OptionKey.A
    )


@pytest.fixture
def sample_user_id():
    return "User1"


@pytest.fixture
def populated_repo(in_memory_repo, sample_question):
    in_memory_repo.seed_questions([sample_question])
    return in_memory_repo


# -------------------------------------------------------------------


def test_seed_and_retrieve_questions(in_memory_repo, sample_question):
    """
    Verifies that questions are correctly inserted into the DB.
    """
    # Arrange
    questions = [sample_question]

    # Act
    in_memory_repo.seed_questions(questions)

    # FIX: Use get_questions_by_ids instead of the deleted get_all_questions
    retrieved = in_memory_repo.get_questions_by_ids([sample_question.id])

    # Assert
    assert len(retrieved) == 1
    assert retrieved[0].id == sample_question.id
    assert retrieved[0].text == sample_question.text


def test_get_questions_by_ids(populated_repo, sample_question):
    """
    Verifies we can fetch specific questions by ID.
    """
    # Arrange
    # Add a second question to ensure filtering works
    q2 = Question(id="Q2", text="B?", options={}, correct_option=OptionKey.A)
    populated_repo.seed_questions([q2])

    # Act
    # We only want Q1
    results = populated_repo.get_questions_by_ids(["Q1"])

    # Assert
    assert len(results) == 1
    assert results[0].id == "Q1"


def test_user_profile_creation_persistence(in_memory_repo, sample_user_id):
    """
    Verifies profile creation and updates.
    """
    # Arrange
    # First call creates it
    profile = in_memory_repo.get_or_create_profile(sample_user_id)

    # FIX: New logic sets streak to 1 for a new user (today's login)
    assert profile.streak_days == 1

    # Act
    profile.streak_days = 5
    in_memory_repo.save_profile(profile)

    # Assert
    # Second call retrieves it
    updated_profile = in_memory_repo.get_or_create_profile(sample_user_id)
    assert updated_profile.streak_days == 5


def test_save_attempt_updates_streak_logic(populated_repo, sample_user_id):
    """
    Verifies that saving an attempt updates the question mastery streak.
    FIX: Uses debug_dump_user_progress to verify state directly.
    Using get_repetition_candidates is flaky because it filters out questions
    attempted today, causing StopIteration.
    """
    # Arrange
    q_id = "Q1"

    # Act 1: Fail the question
    populated_repo.save_attempt(sample_user_id, q_id, is_correct=False)

    # Assert 1: Streak should be 0
    progress_fail = populated_repo.debug_dump_user_progress(sample_user_id)
    entry_fail = next(p for p in progress_fail if p["question_id"] == q_id)
    assert entry_fail["consecutive_correct"] == 0

    # Act 2: Answer correctly
    populated_repo.save_attempt(sample_user_id, q_id, is_correct=True)

    # Assert 2: Streak should increment to 1
    progress_pass = populated_repo.debug_dump_user_progress(sample_user_id)
    entry_pass = next(p for p in progress_pass if p["question_id"] == q_id)
    assert entry_pass["consecutive_correct"] == 1
