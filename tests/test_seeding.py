import pytest
import sqlite3
import logging
from unittest.mock import MagicMock, patch
from src.repository import SQLiteQuizRepository
from src.models import Question, OptionKey


# --- Fixtures ---
@pytest.fixture
def repo():
    return SQLiteQuizRepository(db_path=":memory:")


@pytest.fixture
def sample_q():
    return Question(
        id="101",
        text="Original Text",
        options={OptionKey.A: "A", OptionKey.B: "B", OptionKey.C: "C", OptionKey.D: "D"},
        correct_option=OptionKey.A,
        explanation="Exp"
    )


# --- Tests ---

def test_smart_seed_resets_progress_on_answer_change(repo, sample_q):
    """
    Covers: if old_q and old_q.correct_option != new_q.correct_option:
                cursor.execute("DELETE FROM user_progress ...")
    """
    user_id = "User1"

    # 1. Initial Seed (Answer is A)
    repo.seed_questions([sample_q])

    # 2. User answers correctly
    repo.save_attempt(user_id, sample_q.id, is_correct=True)

    # Verify progress exists
    assert len(repo.get_incorrect_question_ids(user_id)) == 0  # It's correct, so not in incorrect list
    # Double check DB directly to be sure record exists
    with repo._get_connection() as conn:
        assert conn.execute("SELECT count(*) FROM user_progress").fetchone()[0] == 1

    # 3. Re-seed with CHANGED Answer (A -> B)
    updated_q = sample_q.model_copy(update={"correct_option": OptionKey.B})
    repo.seed_questions([updated_q])

    # 4. Assertions
    # Progress should be DELETED
    with repo._get_connection() as conn:
        count = conn.execute("SELECT count(*) FROM user_progress").fetchone()[0]
        assert count == 0

    # Question should be UPDATED
    stored_q = repo.get_question_by_id(sample_q.id)
    assert stored_q.correct_option == OptionKey.B


def test_smart_seed_preserves_progress_on_text_change(repo, sample_q):
    """
    Covers: The 'else' path (implicit) where delete is NOT called.
    """
    user_id = "User1"

    # 1. Initial Seed
    repo.seed_questions([sample_q])
    repo.save_attempt(user_id, sample_q.id, is_correct=True)

    # 2. Re-seed with CHANGED TEXT only (Answer stays A)
    updated_q = sample_q.model_copy(update={"text": "New Text"})
    repo.seed_questions([updated_q])

    # 3. Assertions
    # Progress should REMAIN
    with repo._get_connection() as conn:
        count = conn.execute("SELECT count(*) FROM user_progress").fetchone()[0]
        assert count == 1

    # Question should be UPDATED
    stored_q = repo.get_question_by_id(sample_q.id)
    assert stored_q.text == "New Text"


def test_seed_questions_handles_db_error(repo, sample_q, caplog):
    """
    Covers: except sqlite3.Error as e: logger.error(...)
    """
    # We mock the connection to raise an error when cursor() is called
    # or when commit() is called.

    with patch.object(repo, '_get_connection') as mock_conn_getter:
        # Create a mock connection that raises an error on commit
        mock_conn = MagicMock()
        mock_conn.commit.side_effect = sqlite3.Error("Simulated DB Crash")

        # Context manager setup (__enter__ returns the mock_conn)
        mock_conn_getter.return_value.__enter__.return_value = mock_conn

        # Run the method
        with caplog.at_level(logging.ERROR):
            repo.seed_questions([sample_q])

        # Assertions
        assert "Failed to seed questions: Simulated DB Crash" in caplog.text