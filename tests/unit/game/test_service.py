from unittest.mock import Mock, patch

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
    repo = Mock()
    repo.get_or_create_profile.return_value = UserProfile(
        user_id="test_user",
        preferred_language=Language.PL,
        has_completed_onboarding=True,
    )
    repo.save_attempt = Mock()
    repo.save_profile = Mock()
    return repo


@pytest.fixture
def service(mock_repo):
    """Create GameService with user_id."""
    return GameService(mock_repo, user_id="test_user")


@pytest.fixture
def sample_question():
    return Question(
        id="Q1",
        text="Test question?",
        options={
            OptionKey.A: "Option A",
            OptionKey.B: "Option B",
            OptionKey.C: "Option C",
            OptionKey.D: "Option D",
        },
        correct_option=OptionKey.A,
        explanation="Test explanation",
        category="Test Category",
    )


class TestDashboardStats:
    def test_get_dashboard_stats_calculates_correctly(self, service, mock_repo):
        mock_repo.get_category_stats.return_value = [
            {"category": "BHP", "total": 100, "mastered": 50},
            {"category": "Prawo", "total": 50, "mastered": 25},
        ]

        result = service.get_dashboard_stats("test_user")

        assert result["total_questions"] == 150
        assert result["total_mastered"] == 75
        assert result["global_progress"] == 0.5


class TestDailySprintFlow:
    def test_start_daily_sprint_with_questions(
        self, service, mock_repo, sample_question
    ):
        candidates = [
            QuestionCandidate(question=sample_question, streak=0, is_seen=False)
        ]
        mock_repo.get_repetition_candidates.return_value = candidates

        with patch(
            "src.quiz.domain.spaced_repetition.SpacedRepetitionSelector.select"
        ) as mock_select:
            mock_select.return_value = [sample_question]

            service.start_daily_sprint("test_user")

            assert st.session_state.screen == "quiz"
            assert st.session_state.quiz_title == "🚀 Codzienny Sprint"
            assert len(st.session_state.quiz_questions) > 0


class TestCategoryMode:
    def test_start_category_mode_with_questions(self, service, mock_repo):
        questions = [
            Question(
                id="Q1",
                text="Test?",
                options={OptionKey.A: "A"},
                correct_option=OptionKey.A,
                category="BHP",
            )
        ]
        mock_repo.get_questions_by_category.return_value = questions

        # Don't patch session_state - use the autouse fixture from conftest
        service.start_category_mode("test_user", "BHP")

        mock_repo.get_questions_by_category.assert_called_once()
        assert st.session_state.screen == "quiz"
        assert st.session_state.quiz_title == "📚 BHP"

    @patch("streamlit.toast")
    def test_start_category_mode_no_questions(self, mock_toast, service, mock_repo):
        mock_repo.get_questions_by_category.return_value = []

        service.start_category_mode("test_user", "BHP")

        mock_toast.assert_called_once()


class TestOnboarding:
    def test_start_onboarding_creates_tutorial(self, service, mock_repo):
        # Don't patch session_state - use the autouse fixture
        service.start_onboarding("test_user")

        # Should save profile with onboarding complete
        mock_repo.save_profile.assert_called_once()

        # Verify session state was set correctly
        assert st.session_state.screen == "quiz"
        assert st.session_state.quiz_title == "🎓 Szkolenie Wstępne"
        assert len(st.session_state.quiz_questions) == 1


class TestAnswerSubmission:
    def test_submit_answer_correct(self, service, mock_repo, sample_question):
        # Initialize session state
        st.session_state.score = 0
        st.session_state.answers_history = []
        st.session_state.quiz_errors = []
        st.session_state.last_feedback = {}

        service.submit_answer("test_user", sample_question, OptionKey.A)

        assert st.session_state.score == 1
        assert st.session_state.feedback_mode is True
        mock_repo.save_attempt.assert_called_once_with("test_user", "Q1", True)

    def test_submit_answer_incorrect(self, service, mock_repo, sample_question):
        st.session_state.score = 0
        st.session_state.answers_history = []
        st.session_state.quiz_errors = []
        st.session_state.last_feedback = {}

        service.submit_answer("test_user", sample_question, OptionKey.B)

        assert st.session_state.score == 0
        assert "Q1" in st.session_state.quiz_errors
        mock_repo.save_attempt.assert_called_once_with("test_user", "Q1", False)


class TestQuizNavigation:
    def test_next_question_advances_index(self, service, sample_question):
        st.session_state.current_index = 0
        st.session_state.quiz_questions = [sample_question, sample_question]
        st.session_state.feedback_mode = True

        service.next_question()

        assert st.session_state.current_index == 1
        assert st.session_state.feedback_mode is False

    def test_next_question_finishes_quiz(self, service, sample_question):
        st.session_state.current_index = 14
        st.session_state.quiz_questions = [sample_question] * 15
        st.session_state.feedback_mode = True

        service.next_question()

        assert st.session_state.screen == "summary"


class TestLanguageUpdate:
    def test_update_language_saves_profile(self, service, mock_repo):
        # Don't patch st.rerun - just verify the logic
        with patch("streamlit.rerun"):
            service.update_language("test_user", "en")

        # Should fetch profile and save with new language
        assert mock_repo.get_or_create_profile.called
        assert mock_repo.save_profile.called
