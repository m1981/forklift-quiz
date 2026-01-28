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
    # Use in-memory DB for fast integration testing
    db = DatabaseManager(":memory:")
    repo = SQLiteQuizRepository(db)
    return repo


def create_q(id, category="Gen"):
    return Question(
        id=id,
        text="T",
        options={OptionKey.A: "A"},
        correct_option=OptionKey.A,
        category=category,
    )


def test_get_questions_by_category_filtering(repo):
    """
    Verifies that the SQL query correctly filters by category.
    """
    # Arrange
    qs = [
        create_q("Q1", "BHP"),
        create_q("Q2", "BHP"),
        create_q("Q3", "Law"),
    ]
    repo.seed_questions(qs)

    # Act
    bhp_qs = repo.get_questions_by_category("BHP", "User1", limit=10)
    law_qs = repo.get_questions_by_category("Law", "User1", limit=10)
    empty_qs = repo.get_questions_by_category("NonExistent", "User1", limit=10)

    # Assert
    assert len(bhp_qs) == 2
    assert len(law_qs) == 1
    assert len(empty_qs) == 0
    assert all(q.category == "BHP" for q in bhp_qs)


@patch("src.config.GameConfig.MASTERY_THRESHOLD", 3)
def test_get_mastery_percentage_calculation(repo):
    """
    Verifies the SQL logic for calculating mastery (streak >= 3).
    FIX: Patched MASTERY_THRESHOLD to 3 to match the test expectation (0.25).
    """
    user_id = "User1"
    # Seed 4 questions in "BHP"
    qs = [create_q(f"Q{i}", "BHP") for i in range(4)]
    repo.seed_questions(qs)

    # 1. Mastered (Streak 3)
    repo.save_attempt(user_id, "Q0", True)
    repo.save_attempt(user_id, "Q0", True)
    repo.save_attempt(user_id, "Q0", True)

    # 2. Learning (Streak 1) - Not Mastered (Threshold is 3)
    repo.save_attempt(user_id, "Q1", True)

    # 3. Failed (Streak 0) - Not Mastered
    repo.save_attempt(user_id, "Q2", False)

    # 4. Untouched - Not Mastered

    # Act
    percent = repo.get_mastery_percentage(user_id, "BHP")

    # Assert
    # 1 mastered out of 4 total = 0.25
    assert percent == 0.25


def test_get_mastery_percentage_empty_category(repo):
    """Edge case: Division by zero check."""
    percent = repo.get_mastery_percentage("User1", "EmptyCat")
    assert percent == 0.0


def test_debug_dump_user_progress(repo):
    """
    Verifies the debug tool returns data.
    """
    user_id = "UserDebug"
    repo.save_attempt(user_id, "Q1", True)

    dump = repo.debug_dump_user_progress(user_id)

    assert len(dump) == 1
    assert dump[0]["question_id"] == "Q1"
    assert dump[0]["is_correct"] == 1


def test_get_category_stats_aggregates_correctly(repo):
    """
    Verifies the complex SQL aggregation in get_category_stats.
    Targeting lines 68-113 of sqlite_repository.py
    """
    user_id = "StatsUser"

    # 1. Seed Data
    # Cat A: 2 Questions. 1 Mastered, 1 New.
    q1 = create_q("A1", "CatA")
    q2 = create_q("A2", "CatA")

    # Cat B: 1 Question. 1 Failed (In Progress).
    q3 = create_q("B1", "CatB")

    repo.seed_questions([q1, q2, q3])

    # 2. Create Progress
    # Master A1 (Streak 3)
    repo.save_attempt(user_id, "A1", True)
    repo.save_attempt(user_id, "A1", True)
    repo.save_attempt(user_id, "A1", True)

    # Fail B1 (Streak 0)
    repo.save_attempt(user_id, "B1", False)

    # 3. Act
    stats = repo.get_category_stats(user_id)

    # 4. Assert
    # We expect a list of dicts. Let's find CatA
    stat_a = next(s for s in stats if s["category"] == "CatA")
    assert stat_a["total"] == 2
    assert stat_a["mastered"] == 1

    stat_b = next(s for s in stats if s["category"] == "CatB")
    assert stat_b["total"] == 1
    assert stat_b["mastered"] == 0
