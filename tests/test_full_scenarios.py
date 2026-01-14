# Why this is "Commercial Grade"
# Speed: This test runs in ~0.01 seconds. A Selenium test would take ~10 seconds. You can run thousands of these.
# Resilience: If you change the button color or the CSS class, this test does not break. It only breaks if the logic changes.
# Readability: A Junior Developer or a Product Manager can read the test and understand exactly what the Onboarding Flow is supposed to do.
# Edge Case Handling: You can easily write a test_onboarding_failure_path where the user answers incorrectly, just by changing .answer_question(OptionKey.A) to .answer_question(OptionKey.B).

import pytest
from unittest.mock import Mock
from src.game.core import GameContext
from src.game.director import GameDirector
from src.game.flows import OnboardingFlow
from src.quiz.domain.models import OptionKey
from tests.drivers.game_driver import GameDriver


def test_full_onboarding_flow_happy_path():
    # 1. Setup (The "Rig")
    mock_repo = Mock()
    context = GameContext(user_id="NewUser", repo=mock_repo)
    director = GameDirector(context)
    driver = GameDriver(director)

    # 2. Start the Game
    director.start_flow(OnboardingFlow())

    # 3. Play the Game (Fluent Interface)
    (
        driver
        .assert_on_screen("TEXT", title_contains="Witaj")
        .click_next()

        .assert_on_screen("TEXT", title_contains="Zasady")
        .click_next()

        .assert_on_screen("QUESTION")  # The Tutorial Question
        .answer_question(OptionKey.A)  # Correct Answer

        .assert_on_screen("FEEDBACK")
        .next_question()

        .assert_on_screen("TEXT", title_contains="Szkolenie Zakończone")
        .click_next()

        .assert_on_screen("EMPTY")  # Flow Finished
    )

    # 4. Verify Side Effects (Did we save the result?)
    # We check the repo mock to ensure the engine actually did its job
    mock_repo.save_attempt.assert_called()