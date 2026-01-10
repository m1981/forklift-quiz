import pytest
import sqlite3
from src.models import Question, OptionKey
from src.repository import SQLiteQuizRepository


# --- Fixtures ---
@pytest.fixture
def repo():
    """
    Creates a repository instance using an in-memory database.
    """
    return SQLiteQuizRepository(db_path=":memory:")


@pytest.fixture
def sample_question():
    return Question(
        id="101",
        text="Original Text",
        options={OptionKey.A: "Opt A", OptionKey.B: "Opt B", OptionKey.C: "Opt C", OptionKey.D: "Opt D"},
        correct_option=OptionKey.A,
        explanation="Original Explanation"
    )


# --- Tests ---

def test_seed_new_question(repo, sample_question):
    """Scenario: First time app startup."""
    repo.seed_questions([sample_question])

    stored = repo.get_question_by_id("101")
    assert stored is not None
    assert stored.text == "Original Text"


def test_update_non_critical_data_preserves_progress(repo, sample_question):
    """Scenario: Admin fixes a typo. User progress should stay."""
    # 1. Setup
    repo.seed_questions([sample_question])
    repo.save_attempt(user_id="UserA", question_id="101", is_correct=True)

    # Verify initial state
    # We use the repo's internal connection to verify raw SQL state
    with repo._get_connection() as conn:
        count = \
        conn.execute("SELECT count(*) FROM user_progress WHERE user_id='UserA' AND question_id='101'").fetchone()[0]
        assert count == 1

    # 2. Action: Update Text
    updated_q = sample_question.model_copy(update={"text": "Fixed Typo"})
    repo.seed_questions([updated_q])

    # 3. Assertions
    stored = repo.get_question_by_id("101")
    assert stored.text == "Fixed Typo"

    # Progress should STILL exist
    with repo._get_connection() as conn:
        count = \
        conn.execute("SELECT count(*) FROM user_progress WHERE user_id='UserA' AND question_id='101'").fetchone()[0]
        assert count == 1


def test_update_critical_data_resets_progress(repo, sample_question):
    """Scenario: Answer Key changes. User progress must be wiped."""
    # 1. Setup
    repo.seed_questions([sample_question])
    repo.save_attempt(user_id="UserA", question_id="101", is_correct=True)

    # 2. Action: Update Correct Option (A -> B)
    updated_q = sample_question.model_copy(update={"correct_option": OptionKey.B})
    repo.seed_questions([updated_q])

    # 3. Assertions
    stored = repo.get_question_by_id("101")
    assert stored.correct_option == OptionKey.B

    # Progress should be DELETED
    with repo._get_connection() as conn:
        count = \
        conn.execute("SELECT count(*) FROM user_progress WHERE user_id='UserA' AND question_id='101'").fetchone()[0]
        assert count == 0