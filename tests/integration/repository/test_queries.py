# ==============================================================================
# ARCHITECTURE: INTEGRATION TEST (ADAPTER LAYER)
# ------------------------------------------------------------------------------
# GOAL: Verify Data Persistence and SQL Logic.
# CONSTRAINTS:
#   1. DATABASE: Use a real SQLite instance (In-Memory or Temp File).
#   2. SCOPE: Test CRUD operations, Complex Queries, and Data Integrity.
# ==============================================================================
from unittest.mock import patch

import pytest

from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.domain.models import OptionKey, Question


@pytest.fixture
def repo():
    db = DatabaseManager(":memory:")
    repo = SQLiteQuizRepository(db)
    yield repo
    # Cleanup: Close the database connection
    db.close()


def create_q(id, category="Gen"):
    return Question(
        id=id,
        text="T",
        options={OptionKey.A: "A"},
        correct_option=OptionKey.A,
        category=category,
    )


@patch("src.config.GameConfig.MASTERY_THRESHOLD", 3)
def test_get_repetition_candidates_logic(repo):
    """
    Verify SQL logic for Spaced Repetition:
    1. Unseen questions -> Candidate
    2. Seen & Low Streak (<3) -> Candidate
    3. Seen & High Streak (>=3) & Recent (<3 days) -> HIDDEN
    4. Seen & High Streak (>=3) & Old (>3 days) -> Candidate (Review)

    FIX: Patched MASTERY_THRESHOLD to 3.
    FIX: Manually inserted Q_Learning with past date to avoid daily filter.
    """
    user_id = "User1"

    # 1. Seed Questions
    qs = [
        create_q("Q_New"),
        create_q("Q_Learning"),
        create_q("Q_Mastered_Recent"),
        create_q("Q_Mastered_Old"),
    ]
    repo.seed_questions(qs)

    # 2. Setup Progress
    conn = repo._get_connection()

    # Q_Learning: Streak 1 (Should show)
    # We insert it as 'yesterday' so it's not hidden by the "attempted today" filter
    conn.execute(
        """INSERT OR REPLACE INTO user_progress
        (user_id, question_id, consecutive_correct, timestamp)
        VALUES (?, ?, ?, date('now', '-1 day'))""",
        (user_id, "Q_Learning", 1),
    )

    # Q_Mastered_Recent: Streak 3, Just now (Should be HIDDEN)
    conn.execute(
        """INSERT OR REPLACE INTO user_progress
        (user_id, question_id, consecutive_correct, timestamp)
        VALUES (?, ?, ?, date('now'))""",
        (user_id, "Q_Mastered_Recent", 3),
    )

    # Q_Mastered_Old: Streak 3, 5 days ago (Should show)
    conn.execute(
        """INSERT OR REPLACE INTO user_progress
        (user_id, question_id, consecutive_correct, timestamp)
        VALUES (?, ?, ?, date('now', '-5 days'))""",
        (user_id, "Q_Mastered_Old", 3),
    )
    conn.commit()

    # 3. Act
    candidates = repo.get_repetition_candidates(user_id)
    candidate_ids = {c.question.id for c in candidates}

    # 4. Assert
    assert "Q_New" in candidate_ids
    assert "Q_Learning" in candidate_ids
    assert "Q_Mastered_Old" in candidate_ids

    # The critical check:
    assert "Q_Mastered_Recent" not in candidate_ids
