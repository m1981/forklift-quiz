import pytest

from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.domain.models import OptionKey, Question


@pytest.fixture
def repo():
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


def test_get_repetition_candidates_logic(repo):
    """
    Verify SQL logic for Spaced Repetition:
    1. Unseen questions -> Candidate
    2. Seen & Low Streak (<3) -> Candidate
    3. Seen & High Streak (>=3) & Recent (<3 days) -> HIDDEN
    4. Seen & High Streak (>=3) & Old (>3 days) -> Candidate (Review)
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
    # Q_Learning: Streak 1 (Should show)
    repo.save_attempt(user_id, "Q_Learning", is_correct=True)

    # Q_Mastered_Recent: Streak 3, Just now (Should be HIDDEN)
    # We need to manually inject this to control the timestamp
    conn = repo._get_connection()
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
