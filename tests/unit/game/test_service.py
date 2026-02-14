from datetime import date, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
import streamlit as st

from src.game.service import GameService
from src.quiz.domain.models import (
    Language,
    OptionKey,
    Question,
    QuestionCandidate,
    UserProfile,
)


@pytest.fixture
def mock_repo():
    """Mock repository with common methods."""
    repo = Mock()
    repo.get_or_create_profile.return_value = UserProfile(
        user_id="test_user",
        streak_days=5,
        last_login=date.today(),
        daily_goal=3,
        daily_progress=1,
        has_completed_onboarding=True,
        preferred_language=Language.PL,
    )
    return repo


@pytest.fixture
def service(mock_repo):
    """GameService instance with mocked repo."""
    return GameService(mock_repo)


@pytest.fixture
def sample_question():
    """Sample question for testing."""
    return Question(
        id="Q1",
        text="Test question?",
        options={OptionKey.A: "Option A", OptionKey.B: "Option B"},
        correct_option=OptionKey.A,
        explanation="Test explanation",
        category="Test Category",
    )


@pytest.fixture
def mock_session_state():
    """Mock Streamlit session state."""
    return MagicMock()


class TestDashboardStats:
    def test_get_dashboard_stats_calculates_correctly(self, service, mock_repo):
        """Test dashboard stats calculation with real data."""
        mock_repo.get_category_stats.return_value = [
            {"category": "BHP", "total": 10, "mastered": 7},
            {"category": "Prawo", "total": 15, "mastered": 5},
        ]

        stats = service.get_dashboard_stats("test_user")

        assert stats["total_questions"] == 25
        assert stats["total_mastered"] == 12
        assert stats["global_progress"] == 12 / 25
        assert len(stats["categories"]) == 2
        assert stats["preferred_language"] == "pl"

    def test_get_dashboard_stats_with_demo_slug(self, service, mock_repo):
        """Test dashboard uses demo logo when slug provided."""
        mock_repo.get_category_stats.return_value = []

        with patch("src.config.GameConfig.get_demo_logo_path") as mock_logo:
            mock_logo.return_value = "assets/logos/demo.png"
            service.get_dashboard_stats("test_user", demo_slug="acme-corp")

            mock_logo.assert_called_once_with("acme-corp")

    def test_get_dashboard_stats_calculates_finish_date(self, service, mock_repo):
        """Test finish date calculation based on remaining questions."""
        mock_repo.get_category_stats.return_value = [
            {"category": "BHP", "total": 100, "mastered": 80},
        ]

        stats = service.get_dashboard_stats("test_user")

        # 20 remaining / 10 per day = 2 days
        assert stats["days_left"] == 2
        expected_date = (date.today() + timedelta(days=2)).strftime("%d %b")
        assert stats["finish_date_str"] == expected_date

    def test_get_dashboard_stats_handles_zero_questions(self, service, mock_repo):
        """Test dashboard with no questions."""
        mock_repo.get_category_stats.return_value = []

        stats = service.get_dashboard_stats("test_user")

        assert stats["total_questions"] == 0
        assert stats["total_mastered"] == 0
        assert stats["global_progress"] == 0.0
        assert stats["days_left"] == 0

    def test_get_dashboard_stats_truncates_long_category_names(
        self, service, mock_repo
    ):
        """Test that long category names are truncated."""
        mock_repo.get_category_stats.return_value = [
            {"category": "A" * 50, "total": 10, "mastered": 5},
        ]

        stats = service.get_dashboard_stats("test_user")

        cat = stats["categories"][0]
        # Truncation adds "..." so max length is 30 + 3 = 33, but we check <= 33
        assert len(cat["name"]) <= 33
        assert cat["name"].endswith("...")


class TestDailySprintFlow:
    def test_start_daily_sprint_with_questions(
        self, service, mock_repo, sample_question, mock_session_state
    ):
        """Test starting daily sprint with available questions."""
        candidates = [
            QuestionCandidate(question=sample_question, streak=0, is_seen=False)
        ]
        mock_repo.get_repetition_candidates.return_value = candidates

        with patch.object(st, "session_state", mock_session_state):
            with patch.object(st, "rerun") as mock_rerun:
                service.start_daily_sprint("test_user")

                assert mock_session_state.screen == "quiz"
                assert mock_session_state.quiz_title == "🚀 Codzienny Sprint"
                assert len(mock_session_state.quiz_questions) > 0
                mock_rerun.assert_called_once()

    def test_start_daily_sprint_no_questions(self, service, mock_repo):
        """Test daily sprint when no questions available."""
        mock_repo.get_repetition_candidates.return_value = []

        with patch.object(st, "toast") as mock_toast:
            service.start_daily_sprint("test_user")

            mock_toast.assert_called_once()
            assert "opanowane" in mock_toast.call_args[0][0].lower()


class TestCategoryMode:
    def test_start_category_mode_with_questions(
        self, service, mock_repo, sample_question, mock_session_state
    ):
        """Test starting category mode with questions."""
        mock_repo.get_questions_by_category.return_value = [sample_question]

        with patch.object(st, "session_state", mock_session_state):
            with patch.object(st, "rerun") as mock_rerun:
                service.start_category_mode("test_user", "BHP")

                assert mock_session_state.screen == "quiz"
                assert "BHP" in mock_session_state.quiz_title
                mock_rerun.assert_called_once()

    def test_start_category_mode_no_questions(self, service, mock_repo):
        """Test category mode when no questions available."""
        mock_repo.get_questions_by_category.return_value = []

        with patch.object(st, "toast") as mock_toast:
            service.start_category_mode("test_user", "BHP")

            mock_toast.assert_called_once()
            assert "BHP" in mock_toast.call_args[0][0]


class TestOnboarding:
    def test_start_onboarding_creates_tutorial(
        self, service, mock_repo, mock_session_state
    ):
        """Test onboarding creates tutorial question and marks complete."""
        profile = UserProfile(user_id="test_user", has_completed_onboarding=False)
        mock_repo.get_or_create_profile.return_value = profile

        with patch.object(st, "session_state", mock_session_state):
            with patch.object(st, "rerun") as mock_rerun:
                service.start_onboarding("test_user")

                assert mock_session_state.screen == "quiz"
                assert "Szkolenie" in mock_session_state.quiz_title
                assert len(mock_session_state.quiz_questions) == 1

                # Verify tutorial question structure
                tutorial_q = mock_session_state.quiz_questions[0]
                assert tutorial_q.id == "TUT-01"
                assert tutorial_q.category == "Tutorial"
                assert tutorial_q.correct_option == OptionKey.A

                # Verify profile updated
                assert profile.has_completed_onboarding is True
                mock_repo.save_profile.assert_called_once_with(profile)
                mock_rerun.assert_called_once()


class TestAnswerSubmission:
    def test_submit_answer_correct(
        self, service, mock_repo, sample_question, mock_session_state
    ):
        """Test submitting correct answer."""
        mock_session_state.score = 0
        mock_session_state.answers_history = []
        mock_session_state.quiz_errors = []

        with patch.object(st, "session_state", mock_session_state):
            service.submit_answer("test_user", sample_question, OptionKey.A)

            assert mock_session_state.score == 1
            assert mock_session_state.answers_history == [True]
            assert mock_session_state.feedback_mode is True
            assert mock_session_state.last_feedback["is_correct"] is True
            assert sample_question.id not in mock_session_state.quiz_errors

            mock_repo.save_attempt.assert_called_once_with(
                "test_user", sample_question.id, True
            )

    def test_submit_answer_incorrect(
        self, service, mock_repo, sample_question, mock_session_state
    ):
        """Test submitting incorrect answer."""
        mock_session_state.score = 0
        mock_session_state.answers_history = []
        mock_session_state.quiz_errors = []

        with patch.object(st, "session_state", mock_session_state):
            service.submit_answer("test_user", sample_question, OptionKey.B)

            assert mock_session_state.score == 0
            assert mock_session_state.answers_history == [False]
            assert mock_session_state.feedback_mode is True
            assert mock_session_state.last_feedback["is_correct"] is False
            assert sample_question.id in mock_session_state.quiz_errors

            mock_repo.save_attempt.assert_called_once_with(
                "test_user", sample_question.id, False
            )


class TestQuizNavigation:
    def test_next_question_advances_index(self, service, mock_session_state):
        """Test next_question advances to next question."""
        mock_session_state.current_index = 0
        mock_session_state.quiz_questions = [Mock(), Mock(), Mock()]
        mock_session_state.feedback_mode = True
        mock_session_state.last_feedback = {"is_correct": True}

        with patch.object(st, "session_state", mock_session_state):
            service.next_question()

            assert mock_session_state.current_index == 1
            assert mock_session_state.feedback_mode is False
            assert mock_session_state.last_feedback is None

    def test_next_question_finishes_quiz(self, service, mock_session_state):
        """Test next_question transitions to summary when quiz ends."""
        mock_session_state.current_index = 2
        mock_session_state.quiz_questions = [Mock(), Mock(), Mock()]
        mock_session_state.feedback_mode = True

        with patch.object(st, "session_state", mock_session_state):
            service.next_question()

            assert mock_session_state.screen == "summary"


class TestLanguageUpdate:
    def test_update_language_saves_profile(self, service, mock_repo):
        """Test updating user language preference."""
        profile = UserProfile(user_id="test_user", preferred_language=Language.PL)
        mock_repo.get_or_create_profile.return_value = profile

        service.update_language("test_user", "en")

        assert profile.preferred_language == Language.EN
        mock_repo.save_profile.assert_called_once_with(profile)
