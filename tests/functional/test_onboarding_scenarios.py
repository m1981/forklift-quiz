# ==============================================================================
# ARCHITECTURE: FUNCTIONAL TEST (USER FLOWS)
# ------------------------------------------------------------------------------
# GOAL: Verify End-to-End User Scenarios via the GameDriver.
# CONSTRAINTS:
#   1. DRIVER: MUST use 'tests.helpers.game_driver.GameDriver'.
#   2. I/O: MOCKED. Use 'unittest.mock' for the Repository/Database.
# ==============================================================================
from unittest.mock import Mock

from src.game.core import GameContext
from src.game.director import GameDirector
from src.game.flows import OnboardingFlow
from src.quiz.domain.models import OptionKey, UserProfile
from tests.helpers.game_driver import GameDriver


def test_full_onboarding_flow_happy_path():
    # 1. Setup (The "Rig")
    mock_repo = Mock()
    # We must mock the profile so the flow doesn't crash
    # when saving 'has_completed_onboarding'
    mock_repo.get_or_create_profile.return_value = UserProfile(user_id="NewUser")

    # --- FIX 1: Mock methods required by DashboardStep and QuestionLoopStep ---
    # DashboardStep iterates over this result, so it must be a list
    mock_repo.get_category_stats.return_value = []
    # QuestionLoopStep uses this for the header progress bar
    mock_repo.get_mastery_percentage.return_value = 0.0
    # --------------------------------------------------------------------------

    context = GameContext(user_id="NewUser", repo=mock_repo)
    director = GameDirector(context)
    driver = GameDriver(director)

    # 2. Start the Game
    director.start_flow(OnboardingFlow())

    # 3. Play the Game (Fluent Interface)
    (
        driver.assert_on_screen("TEXT", title_contains="Witaj")
        .click_next()
        .assert_on_screen("QUESTION")  # The Tutorial Question
        .answer_question(OptionKey.A)  # Correct Answer
        .assert_on_screen("FEEDBACK")
        .next_question()
        .assert_on_screen("TEXT", title_contains="Szkolenie Zakończone")
        .click_next()
        # --- FIX 2: Expect DASHBOARD instead of EMPTY ---
        .assert_on_screen("DASHBOARD")
    )

    # 4. Verify Side Effects
    # Ensure we marked the user as onboarded
    mock_repo.save_profile.assert_called()
    # Ensure we saved the answer
    mock_repo.save_attempt.assert_called()
