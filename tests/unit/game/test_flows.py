from unittest.mock import Mock, patch

import pytest

from src.game.core import GameContext
from src.game.flows import DailySprintFlow, OnboardingFlow
from src.game.steps import QuestionLoopStep, SummaryStep, TextStep
from src.quiz.domain.models import OptionKey, Question, QuestionCandidate, UserProfile

# --- Fixtures ---


@pytest.fixture
def mock_repo():
    repo = Mock()
    # Setup default profile
    repo.get_or_create_profile.return_value = UserProfile(
        user_id="TestUser", daily_progress=0, daily_goal=3
    )
    return repo


@pytest.fixture
def context(mock_repo):
    return GameContext(user_id="TestUser", repo=mock_repo)


@pytest.fixture
def sample_candidate():
    q = Question(id="Q1", text="T", options={}, correct_option=OptionKey.A)
    return QuestionCandidate(question=q, streak=0, is_seen=False)


# --- Tests ---


class TestDailySprintFlow:
    def test_builds_standard_flow_with_questions(
        self, context, mock_repo, sample_candidate
    ):
        """
        Verifies that if candidates are available, we get a QuestionLoop + Summary.
        """
        # Arrange
        # 1. Mock the Repo to return raw candidates
        mock_repo.get_repetition_candidates.return_value = [sample_candidate] * 20

        # 2. Mock the Selector to return a subset (simulating the logic)
        # We patch the class where it is imported in flows.py
        with patch("src.game.flows.SpacedRepetitionSelector") as MockSelector:
            selector_instance = MockSelector.return_value
            # Simulate selecting 15 questions
            selector_instance.select.return_value = [sample_candidate.question] * 15

            flow = DailySprintFlow()

            # Act
            steps = flow.build_steps(context)

        # Assert
        assert len(steps) == 2

        # Step 1: Quiz Loop
        assert isinstance(steps[0], QuestionLoopStep)
        assert len(steps[0].questions) == 15
        assert steps[0].flow_title == "🚀 Codzienny Sprint"

        # Step 2: Summary
        assert isinstance(steps[1], SummaryStep)

    def test_handles_no_questions_available(self, context, mock_repo):
        """
        Verifies that if the Selector returns nothing
        (e.g. everything mastered recently),
        we show a 'Congratulations' message instead of crashing.
        """
        # Arrange
        mock_repo.get_repetition_candidates.return_value = []

        with patch("src.game.flows.SpacedRepetitionSelector") as MockSelector:
            selector_instance = MockSelector.return_value
            selector_instance.select.return_value = []  # Empty selection

            flow = DailySprintFlow()

            # Act
            steps = flow.build_steps(context)

        # Assert
        assert len(steps) == 1
        assert isinstance(steps[0], TextStep)
        assert "Gratulacje" in steps[0].payload.title


class TestOnboardingFlow:
    def test_builds_fixed_tutorial_sequence(self, context):
        """
        Verifies the fixed sequence of the Onboarding tutorial.
        """
        # Arrange
        flow = OnboardingFlow()

        # Act
        steps = flow.build_steps(context)

        # Assert
        assert len(steps) == 3

        # 1. Welcome Text
        assert isinstance(steps[0], TextStep)
        assert "Witaj" in steps[0].payload.title

        # 2. Fixed Question Loop
        assert isinstance(steps[1], QuestionLoopStep)
        assert len(steps[1].questions) == 1
        assert steps[1].questions[0].id == "TUT-01"  # Verify hardcoded ID
        assert steps[1].flow_title == "🎓 Szkolenie Wstępne"

        # 3. Outro Text
        assert isinstance(steps[2], TextStep)
        assert "Zakończone" in steps[2].payload.title
