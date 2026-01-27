# ==============================================================================
# ARCHITECTURE: FUNCTIONAL TEST (USER FLOWS)
# ------------------------------------------------------------------------------
# GOAL: Verify End-to-End User Scenarios via the GameDriver.
# CONSTRAINTS:
#   1. DRIVER: MUST use 'tests.helpers.game_driver.GameDriver'.
#   2. I/O: MOCKED. Use 'unittest.mock' for the Repository/Database.
# ==============================================================================
from unittest.mock import Mock, patch

from src.game.core import GameContext
from src.game.director import GameDirector
from src.game.flows import DailySprintFlow
from src.quiz.domain.models import OptionKey, Question, QuestionCandidate, UserProfile
from tests.helpers.game_driver import GameDriver

# --- Setup Helpers ---


def create_candidate(id, correct_opt=OptionKey.A):
    q = Question(
        id=id,
        text=f"Question {id}",
        options={OptionKey.A: "A", OptionKey.B: "B"},
        correct_option=correct_opt,
        category="Test",
    )
    return QuestionCandidate(question=q, streak=0, is_seen=False)


def setup_game(candidates):
    mock_repo = Mock()
    mock_repo.get_or_create_profile.return_value = UserProfile(user_id="User")
    mock_repo.get_repetition_candidates.return_value = candidates

    # --- FIX 1: Mock the methods used by DashboardStep and QuestionLoopStep ---
    # DashboardStep iterates over this, so it MUST be a list
    mock_repo.get_category_stats.return_value = []
    # QuestionLoopStep uses this for the header progress bar
    mock_repo.get_mastery_percentage.return_value = 0.0
    # --------------------------------------------------------------------------

    # Mock save_attempt to avoid errors
    mock_repo.save_attempt = Mock()

    context = GameContext(user_id="User", repo=mock_repo)
    director = GameDirector(context)
    driver = GameDriver(director)

    return director, driver, mock_repo


# --- Tests ---


def test_daily_sprint_perfect_run():
    """
    Scenario: User starts a sprint with 3 questions and answers all correctly.
    Verifies: Flow transition, Scoring, Summary display.
    """
    # 1. Arrange
    candidates = [
        create_candidate("Q1", OptionKey.A),
        create_candidate("Q2", OptionKey.B),
        create_candidate("Q3", OptionKey.A),
    ]

    director, driver, _ = setup_game(candidates)

    # Patch the Selector to return our exact 3 questions (deterministic)
    with patch("src.game.flows.SpacedRepetitionSelector") as MockSelector:
        MockSelector.return_value.select.return_value = [c.question for c in candidates]

        # 2. Start
        director.start_flow(DailySprintFlow())

        # 3. Act & Assert (The "Perfect Run")
        (
            driver
            # Q1
            .assert_on_screen("QUESTION", title_contains="Codzienny Sprint")
            .answer_question(OptionKey.A)  # Correct
            .assert_on_screen("FEEDBACK")
            .next_question()
            # Q2
            .assert_on_screen("QUESTION")
            .answer_question(OptionKey.B)  # Correct
            .assert_on_screen("FEEDBACK")
            .next_question()
            # Q3
            .assert_on_screen("QUESTION")
            .answer_question(OptionKey.A)  # Correct
            .assert_on_screen("FEEDBACK")
            .next_question()
            # Summary
            .assert_on_screen("SUMMARY")
            .assert_score(3)  # 3/3 Correct
            .finish_quiz()
            # End - FIX 2: Expect DASHBOARD instead of EMPTY
            .assert_on_screen("DASHBOARD")
        )


def test_daily_sprint_with_mistakes_and_review():
    """
    Scenario: User answers 1 wrong, gets to Summary, chooses 'Review Mistakes',
    and correctly answers the failed question.
    Verifies: Error tracking, Branching logic, Context clearing.
    """
    # 1. Arrange
    candidates = [create_candidate("Q1", OptionKey.A)]  # Just 1 question for simplicity

    director, driver, repo = setup_game(candidates)

    # We need get_questions_by_ids to work for the Review phase
    repo.get_questions_by_ids.return_value = [candidates[0].question]

    with patch("src.game.flows.SpacedRepetitionSelector") as MockSelector:
        MockSelector.return_value.select.return_value = [c.question for c in candidates]

        # 2. Start
        director.start_flow(DailySprintFlow())

        # 3. Act & Assert
        (
            driver
            # Attempt 1: Fail Q1
            .assert_on_screen("QUESTION")
            .answer_question(OptionKey.B)  # WRONG!
            .assert_on_screen("FEEDBACK")
            .next_question()
            # Summary (Score 0)
            .assert_on_screen("SUMMARY")
            .assert_score(0)
            # Branch: Review Mistakes
            .review_mistakes()
            # Review Loop: Q1 again
            .assert_on_screen("QUESTION", title_contains="Poprawa Błędów")
            .answer_question(OptionKey.A)  # Correct this time
            .assert_on_screen("FEEDBACK")
            .next_question()
            # End - FIX 2: Expect DASHBOARD instead of EMPTY
            .assert_on_screen("DASHBOARD")
        )
