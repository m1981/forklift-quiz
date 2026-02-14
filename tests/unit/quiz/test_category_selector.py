from src.quiz.domain.category_selector import CategorySelector
from src.quiz.domain.models import OptionKey, Question


def create_question(id: str, category: str = "BHP") -> Question:
    """Helper to create minimal valid Question objects for testing."""
    return Question(
        id=id,
        text=f"Question {id}",
        category=category,
        options={
            OptionKey.A: "Option A",
            OptionKey.B: "Option B",
            OptionKey.C: "Option C",
            OptionKey.D: "Option D",
        },
        correct_option=OptionKey.A,
        explanation="Test explanation",
    )


def test_prioritizes_weakest_questions():
    """Questions with lower streaks should appear first."""
    questions = [
        (create_question("Q1"), 5),  # Strong
        (create_question("Q2"), 0),  # Weakest
        (create_question("Q3"), 2),  # Medium
    ]

    result = CategorySelector.prioritize_weak_questions(questions, limit=3)

    assert result[0].id == "Q2"  # Streak 0 (weakest)
    assert result[1].id == "Q3"  # Streak 2
    assert result[2].id == "Q1"  # Streak 5 (strongest)


def test_randomizes_equal_streaks():
    """Questions with same streak should be randomized."""
    questions = [(create_question(f"Q{i}"), 0) for i in range(10)]

    # Run multiple times to check randomness
    results = [
        CategorySelector.prioritize_weak_questions(questions, limit=5)
        for _ in range(10)
    ]

    # At least one result should differ (not always same order)
    unique_orders = set(tuple(q.id for q in r) for r in results)
    assert len(unique_orders) > 1, "Results should vary due to randomization"


def test_respects_limit():
    """Should return exactly 'limit' questions."""
    questions = [(create_question(f"Q{i}"), i) for i in range(20)]

    result = CategorySelector.prioritize_weak_questions(questions, limit=5)

    assert len(result) == 5


def test_handles_empty_list():
    """Should return empty list when no questions provided."""
    result = CategorySelector.prioritize_weak_questions([], limit=10)
    assert result == []


def test_limit_exceeds_available():
    """Should return all questions when limit > available."""
    questions = [
        (create_question("Q1"), 0),
        (create_question("Q2"), 1),
    ]

    result = CategorySelector.prioritize_weak_questions(questions, limit=10)

    assert len(result) == 2
