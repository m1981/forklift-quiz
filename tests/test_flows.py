from unittest.mock import Mock

import pytest

from src.game.core import GameContext
from src.game.flows import DailySprintFlow, OnboardingFlow
from src.game.steps import QuestionLoopStep, SummaryStep, TextStep
from src.quiz.domain.models import OptionKey, Question, UserProfile

# --- Fixtures ---


@pytest.fixture
def mock_repo():
    repo = Mock()
    # Default behavior: Return some dummy questions
    repo.get_all_questions.return_value = [
        Question(id="Q1", text="T", options={}, correct_option=OptionKey.A)
    ] * 10
    return repo


@pytest.fixture
def context(mock_repo):
    return GameContext(user_id="TestUser", repo=mock_repo)


# --- Tests ---


class TestDailySprintFlow:
    def test_builds_standard_flow_when_goal_not_met(self, context, mock_repo):
        # Arrange
        # User has 0/3 progress
        mock_repo.get_or_create_profile.return_value = UserProfile(
            user_id="TestUser", daily_progress=0, daily_goal=3
        )

        flow = DailySprintFlow()

        # Act
        steps = flow.build_steps(context)

        # Assert
        assert len(steps) == 3

        # Step 1: Intro Text
        assert isinstance(steps[0], TextStep)
        assert steps[0].payload.title == "Codzienny Sprint 🚀"

        # Step 2: Quiz Loop
        assert isinstance(steps[1], QuestionLoopStep)
        assert len(steps[1].questions) == 10  # Standard limit

        # Step 3: Summary
        assert isinstance(steps[2], SummaryStep)

    def test_builds_bonus_flow_when_goal_met(self, context, mock_repo):
        # Arrange
        # User has 3/3 progress (Goal Met)
        mock_repo.get_or_create_profile.return_value = UserProfile(
            user_id="TestUser", daily_progress=3, daily_goal=3
        )

        flow = DailySprintFlow()

        # Act
        steps = flow.build_steps(context)

        # Assert
        # Step 1 should be Bonus Intro
        assert isinstance(steps[0], TextStep)
        assert steps[0].payload.title == "🔥 Runda Bonusowa"

        # Step 2 should have fewer questions (Limit 5)
        assert isinstance(steps[1], QuestionLoopStep)
        assert len(steps[1].questions) == 5

    def test_handles_no_questions_available(self, context, mock_repo):
        # Arrange
        mock_repo.get_all_questions.return_value = []  # Empty DB
        mock_repo.get_or_create_profile.return_value = UserProfile(
            user_id="U", daily_progress=0
        )

        flow = DailySprintFlow()

        # Act
        steps = flow.build_steps(context)

        # Assert
        assert len(steps) == 1
        assert isinstance(steps[0], TextStep)
        assert steps[0].payload.title == "Brak Pytań"


class TestOnboardingFlow:
    def test_builds_fixed_tutorial_sequence(self, context):
        # Arrange
        flow = OnboardingFlow()

        # Act
        steps = flow.build_steps(context)

        # Assert
        assert len(steps) == 4

        # 1. Welcome
        assert isinstance(steps[0], TextStep)
        assert "Witaj" in steps[0].payload.title

        # 2. Rules
        assert isinstance(steps[1], TextStep)
        assert "Zasady" in steps[1].payload.title

        # 3. Fixed Question
        assert isinstance(steps[2], QuestionLoopStep)
        assert len(steps[2].questions) == 1
        assert steps[2].questions[0].id == "TUT-01"  # Verify hardcoded ID

        # 4. Outro
        assert isinstance(steps[3], TextStep)
        assert "Zakończone" in steps[3].payload.title
