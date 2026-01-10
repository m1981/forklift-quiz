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
def q1():
    return Question(
        id="101",
        text="Question 1",
        options={OptionKey.A: "A", OptionKey.B: "B", OptionKey.C: "C", OptionKey.D: "D"},
        correct_option=OptionKey.A,
        explanation="Exp 1"
    )


@pytest.fixture
def q2():
    return Question(
        id="102",
        text="Question 2",
        options={OptionKey.A: "A", OptionKey.B: "B", OptionKey.C: "C", OptionKey.D: "D"},
        correct_option=OptionKey.B,
        explanation="Exp 2"
    )


# --- Tests for Seeding (Previous Logic) ---

def test_seed_new_question(repo, q1):
    repo.seed_questions([q1])
    stored = repo.get_question_by_id("101")
    assert stored is not None
    assert stored.text == "Question 1"


def test_smart_seeding_resets_on_critical_change(repo, q1):
    # 1. Setup: User answers correctly
    repo.seed_questions([q1])
    repo.save_attempt("UserA", "101", True)

    # 2. Change Answer Key
    q1_updated = q1.model_copy(update={"correct_option": OptionKey.B})
    repo.seed_questions([q1_updated])

    # 3. Verify Progress Deleted
    assert len(repo.get_incorrect_question_ids("UserA")) == 0
    # Double check via raw SQL that the row is gone
    with repo._get_connection() as conn:
        count = conn.execute("SELECT count(*) FROM user_progress").fetchone()[0]
        assert count == 0


# --- NEW Tests for Coverage (The Red Lines) ---

def test_save_attempt_upsert_logic(repo, q1):
    """
    Covers lines 106-114: save_attempt
    Verifies that we can Insert AND Update (Upsert) records.
    """
    repo.seed_questions([q1])

    # 1. Insert (First attempt - Incorrect)
    repo.save_attempt(user_id="UserA", question_id="101", is_correct=False)

    # Verify it's marked incorrect
    incorrect_ids = repo.get_incorrect_question_ids("UserA")
    assert "101" in incorrect_ids

    # 2. Update (Second attempt - Correct)
    # This triggers the 'ON CONFLICT DO UPDATE' clause in SQL
    repo.save_attempt(user_id="UserA", question_id="101", is_correct=True)

    # Verify it's now removed from incorrect list
    incorrect_ids = repo.get_incorrect_question_ids("UserA")
    assert "101" not in incorrect_ids

    # Verify raw state is correct (is_correct = 1)
    with repo._get_connection() as conn:
        row = conn.execute("SELECT is_correct FROM user_progress WHERE user_id='UserA'").fetchone()
        assert row[0] == 1


def test_get_incorrect_question_ids_filtering(repo, q1, q2):
    """
    Covers lines 116-122: get_incorrect_question_ids
    Verifies it only returns questions marked False, and ignores True.
    """
    repo.seed_questions([q1, q2])

    # User gets Q1 Wrong, Q2 Right
    repo.save_attempt("UserA", "101", is_correct=False)
    repo.save_attempt("UserA", "102", is_correct=True)

    # UserB gets Q1 Right (Ensure isolation between users)
    repo.save_attempt("UserB", "101", is_correct=True)

    # Act
    ids = repo.get_incorrect_question_ids("UserA")

    # Assert
    assert ids == ["101"]  # Should contain Q1
    assert "102" not in ids  # Should NOT contain Q2

    # Verify UserB has no incorrect questions
    assert repo.get_incorrect_question_ids("UserB") == []


def test_reset_user_progress(repo, q1, q2):
    """
    Covers lines 124-127: reset_user_progress
    Verifies data deletion for a specific user.
    """
    repo.seed_questions([q1, q2])

    # Setup: UserA has history
    repo.save_attempt("UserA", "101", is_correct=False)
    repo.save_attempt("UserA", "102", is_correct=True)

    # Setup: UserB has history (Should NOT be deleted)
    repo.save_attempt("UserB", "101", is_correct=False)

    # Act: Reset UserA
    repo.reset_user_progress("UserA")

    # Assert UserA is clear
    assert repo.get_incorrect_question_ids("UserA") == []
    with repo._get_connection() as conn:
        count = conn.execute("SELECT count(*) FROM user_progress WHERE user_id='UserA'").fetchone()[0]
        assert count == 0

    # Assert UserB is untouched
    assert repo.get_incorrect_question_ids("UserB") == ["101"]