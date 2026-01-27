from unittest.mock import Mock

from src.game.core import GameContext
from src.game.director import GameDirector
from src.game.flows import CategorySprintFlow
from src.quiz.domain.models import Question
from tests.drivers.game_driver import GameDriver


def test_category_sprint_happy_path():
    # 1. Setup
    mock_repo = Mock()
    mock_repo.get_questions_by_category.return_value = [
        Question(
            id="C1",
            text="Cat Q1",
            options={"A": "1", "B": "2"},
            correct_option="A",
            category="BHP",
        ),
        Question(
            id="C2",
            text="Cat Q2",
            options={"A": "1", "B": "2"},
            correct_option="B",
            category="BHP",
        ),
    ]
    # Mock dashboard stats for the end of the flow
    mock_repo.get_category_stats.return_value = []
    mock_repo.get_mastery_percentage.return_value = 0.0

    context = GameContext(user_id="User", repo=mock_repo)
    director = GameDirector(context)
    driver = GameDriver(director)

    # 2. Start Flow
    director.start_flow(CategorySprintFlow(category="BHP"))

    # 3. Verify
    (
        driver.assert_on_screen("QUESTION", title_contains="BHP")
        .answer_question("A")
        .next_question()
        .assert_on_screen("QUESTION")
        .answer_question("B")
        .next_question()
        .assert_on_screen("SUMMARY")
        .finish_quiz()
        .assert_on_screen("DASHBOARD")
    )

    # Verify repo call
    mock_repo.get_questions_by_category.assert_called_with("BHP", "User", 15)


def test_category_sprint_empty_state():
    """
    GIVEN a category with no questions
    WHEN flow starts
    THEN it should show a text message and exit
    """
    mock_repo = Mock()
    mock_repo.get_questions_by_category.return_value = []  # Empty
    mock_repo.get_category_stats.return_value = []

    context = GameContext(user_id="User", repo=mock_repo)
    director = GameDirector(context)
    driver = GameDriver(director)

    director.start_flow(CategorySprintFlow(category="EmptyCat"))

    (
        driver.assert_on_screen("TEXT", title_contains="Pusto")
        .click_next()
        .assert_on_screen("DASHBOARD")
    )
