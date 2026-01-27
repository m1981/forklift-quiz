# ==============================================================================
# ARCHITECTURE: INTEGRATION TEST (ADAPTER LAYER)
# ------------------------------------------------------------------------------
# GOAL: Verify Data Persistence and SQL Logic.
# CONSTRAINTS:
#   1. DATABASE: Use a real SQLite instance (In-Memory or Temp File).
#   2. SCOPE: Test CRUD operations, Complex Queries, and Data Integrity.
# ==============================================================================
from src.quiz.domain.models import OptionKey, Question


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
    FIX: Uses get_repetition_candidates to verify state instead of deleted methods.
    """
    # Arrange
    q_id = "Q1"

    # Act 1: Fail the question
    populated_repo.save_attempt(sample_user_id, q_id, is_correct=False)

    # Assert 1: Streak should be 0
    candidates_fail = populated_repo.get_repetition_candidates(sample_user_id)
    target_fail = next(c for c in candidates_fail if c.question.id == q_id)
    assert target_fail.streak == 0

    # Act 2: Answer correctly
    populated_repo.save_attempt(sample_user_id, q_id, is_correct=True)

    # Assert 2: Streak should increment to 1
    candidates_pass = populated_repo.get_repetition_candidates(sample_user_id)
    target_pass = next(c for c in candidates_pass if c.question.id == q_id)
    assert target_pass.streak == 1
