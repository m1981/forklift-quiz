from unittest.mock import MagicMock

from src.quiz.domain.models import Question, QuestionCandidate
from src.quiz.domain.spaced_repetition import SpacedRepetitionSelector


def create_candidate(id, streak=0, is_seen=False):
    q = MagicMock(spec=Question)
    q.id = id
    return QuestionCandidate(question=q, streak=streak, is_seen=is_seen)


def test_selector_prioritizes_learning_and_review():
    """
    GIVEN a mix of new, learning (low streak), and review (high streak) questions
    WHEN select is called
    THEN the result should respect the NEW_RATIO (default 0.6 new, 0.4 review)
    """
    # Arrange
    selector = SpacedRepetitionSelector()

    # 10 New Questions
    new_qs = [create_candidate(f"New_{i}", is_seen=False) for i in range(10)]

    # 5 Learning Questions (Seen, Streak < 3)
    learning_qs = [
        create_candidate(f"Learn_{i}", streak=1, is_seen=True) for i in range(5)
    ]

    # 5 Review Questions (Seen, Streak >= 3)
    review_qs = [
        create_candidate(f"Review_{i}", streak=5, is_seen=True) for i in range(5)
    ]

    all_candidates = new_qs + learning_qs + review_qs

    # Act
    # Request 10 questions.
    # Config: NEW_RATIO = 0.6 -> Target: 6 New, 4 Review/Learning
    selected = selector.select(all_candidates, limit=10)

    # Assert
    assert len(selected) == 10

    # Count types in result
    selected_ids = [q.id for q in selected]
    new_count = sum(1 for i in selected_ids if "New" in i)
    review_learning_count = sum(
        1 for i in selected_ids if "Learn" in i or "Review" in i
    )

    # We expect roughly the ratio, but since we have enough candidates,
    # the algorithm should hit the targets exactly.
    assert new_count == 6
    assert review_learning_count == 4


def test_selector_backfills_if_not_enough_new():
    """
    GIVEN mostly review questions and very few new ones
    WHEN select is called
    THEN it should fill the quota with review questions
    """
    selector = SpacedRepetitionSelector()

    # Only 1 New Question
    new_qs = [create_candidate("New_1", is_seen=False)]

    # 20 Review Questions
    review_qs = [
        create_candidate(f"Review_{i}", streak=5, is_seen=True) for i in range(20)
    ]

    all_candidates = new_qs + review_qs

    # Act: Request 10
    selected = selector.select(all_candidates, limit=10)

    # Assert
    assert len(selected) == 10
    # Should have taken the 1 new question
    assert any(q.id == "New_1" for q in selected)
    # The rest (9) should be reviews
    review_count = sum(1 for q in selected if "Review" in q.id)
    assert review_count == 9
