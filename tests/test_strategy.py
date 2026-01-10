import pytest
from unittest.mock import MagicMock
from src.models import Question, OptionKey, UserProfile
from src.strategies import StandardStrategy, ReviewStrategy, DailySprintStrategy


# --- Fixtures ---

@pytest.fixture
def mock_repo():
    """Creates a fake repository that returns controlled data."""
    repo = MagicMock()

    # Default: 10 Questions (IDs "1" to "10")
    questions = [
        Question(id=str(i), text=f"Q{i}", options={"A": "A"}, correct_option="A")
        for i in range(1, 11)
    ]
    repo.get_all_questions.return_value = questions
    return repo


@pytest.fixture
def user_profile():
    return UserProfile(user_id="TestUser", daily_goal=10, daily_progress=0)


# --- Tests ---

def test_standard_strategy(mock_repo):
    strategy = StandardStrategy()
    result = strategy.generate("User1", mock_repo)

    # Should return everything
    assert len(result) == 10
    assert result[0].id == "1"


def test_review_strategy(mock_repo):
    # Setup: User got Q2 and Q5 wrong
    mock_repo.get_incorrect_question_ids.return_value = ["2", "5"]

    strategy = ReviewStrategy()
    result = strategy.generate("User1", mock_repo)

    # Should return exactly those 2
    assert len(result) == 2
    ids = sorted([q.id for q in result])
    assert ids == ["2", "5"]


def test_sprint_strategy_mix(mock_repo, user_profile):
    """
    Scenario: User needs 10 questions.
    Has 2 Incorrect (Q1, Q2).
    Has 3 Attempted Total (Q1, Q2, Q3).
    """
    mock_repo.get_or_create_profile.return_value = user_profile
    mock_repo.get_incorrect_question_ids.return_value = ["1", "2"]
    mock_repo.get_all_attempted_ids.return_value = ["1", "2", "3"]

    strategy = DailySprintStrategy()
    result = strategy.generate("User1", mock_repo)

    # Assertions
    assert len(result) == 10  # Goal is 10

    ids = [q.id for q in result]

    # 1. Must include struggling (Q1, Q2)
    assert "1" in ids
    assert "2" in ids

    # 2. Must include New questions (IDs 4-10)
    # We have 7 new questions available (4,5,6,7,8,9,10).
    # We need 10 total. 2 are struggling. 8 slots left.
    # We take all 7 new questions.
    for i in range(4, 11):
        assert str(i) in ids

    # 3. We still need 1 more to reach 10.
    # It must come from Mastered (Q3 is the only mastered one: Attempted but not Incorrect)
    assert "3" in ids


def test_sprint_strategy_bonus_round(mock_repo):
    """
    Scenario: User has already finished daily goal (Progress=10, Goal=10).
    Should return 5 bonus questions.
    """
    completed_profile = UserProfile(user_id="DoneUser", daily_goal=10, daily_progress=10)
    mock_repo.get_or_create_profile.return_value = completed_profile

    # No history for simplicity
    mock_repo.get_incorrect_question_ids.return_value = []
    mock_repo.get_all_attempted_ids.return_value = []

    strategy = DailySprintStrategy()
    result = strategy.generate("DoneUser", mock_repo)

    assert len(result) == 5  # Bonus round size