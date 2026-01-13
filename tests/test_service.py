import pytest
from unittest.mock import Mock, ANY
from datetime import date, timedelta

from src.quiz.application.service import QuizService
from src.quiz.domain.models import Question, OptionKey, UserProfile, QuizSessionState
from src.quiz.domain.ports import IQuizRepository
from src.quiz.application.strategies import StrategyRegistry, IQuestionStrategy


# --- Fixtures (The "Arrange" Phase) ---

@pytest.fixture
def mock_repo():
    """Creates a strict mock of the Repository Interface."""
    return Mock(spec=IQuizRepository)


@pytest.fixture
def service(mock_repo):
    """Injects the mock repo into the service."""
    return QuizService(mock_repo)


@pytest.fixture
def sample_question():
    return Question(
        id="Q1",
        text="Test Question",
        options={OptionKey.A: "Yes", OptionKey.B: "No"},
        correct_option=OptionKey.A,
        category="Test"
    )


@pytest.fixture
def sample_user():
    return UserProfile(
        user_id="TestUser",
        streak_days=5,
        last_login=date.today() - timedelta(days=1),  # Logged in yesterday
        daily_progress=0,
        daily_goal=3
    )


# --- Tests (The "Act" & "Assert" Phases) ---

class TestQuizService_SubmitAnswer:

    def test_submit_correct_answer_returns_true_and_saves(self, service, mock_repo, sample_question):
        # Arrange
        user_id = "User1"
        mock_repo.was_question_answered_on_date.return_value = False  # Not a duplicate

        # Act
        result = service.submit_answer(user_id, sample_question, OptionKey.A)  # A is correct

        # Assert
        assert result is True
        mock_repo.save_attempt.assert_called_once_with(user_id, "Q1", True)

    def test_submit_incorrect_answer_returns_false_and_saves(self, service, mock_repo, sample_question):
        # Arrange
        user_id = "User1"
        mock_repo.was_question_answered_on_date.return_value = False

        # Act
        result = service.submit_answer(user_id, sample_question, OptionKey.B)  # B is wrong

        # Assert
        assert result is False
        mock_repo.save_attempt.assert_called_once_with(user_id, "Q1", False)

    def test_duplicate_submission_logs_telemetry(self, service, mock_repo, sample_question):
        # Arrange
        user_id = "User1"
        # Simulate that DB says "Yes, this was already answered today"
        mock_repo.was_question_answered_on_date.return_value = True

        # Spy on the telemetry logger
        service.telemetry.logger = Mock()

        # Act
        service.submit_answer(user_id, sample_question, OptionKey.A)

        # Assert
        # We need to look through ALL calls to find the one about duplicates.
        # The decorator logs a metric at the end, which might be the 'last' call.

        found_duplicate_log = False
        for call in service.telemetry.logger.info.call_args_list:
            args, _ = call
            log_message = str(args[0])  # The first arg is the log string
            if "Duplicate Answer Attempt" in log_message:
                found_duplicate_log = True
                break

        assert found_duplicate_log, f"Expected 'Duplicate Answer Attempt' log not found. Calls were: {service.telemetry.logger.info.call_args_list}"


class TestQuizService_StreakLogic:
    """
    Validates the complex business rules around streaks.
    """

    def test_streak_increments_if_last_login_was_yesterday(self, service, mock_repo, sample_user):
        # Arrange
        # User logged in yesterday (streak=5). Today should become 6.
        sample_user.last_login = date.today() - timedelta(days=1)
        mock_repo.get_or_create_profile.return_value = sample_user

        # Act
        service.finalize_session("TestUser")

        # Assert
        # Verify the object passed to save_profile has the correct values
        saved_profile = mock_repo.save_profile.call_args[0][0]
        assert saved_profile.streak_days == 6
        assert saved_profile.last_login == date.today()

    def test_streak_resets_if_login_missed_a_day(self, service, mock_repo, sample_user):
        # Arrange
        # User logged in 2 days ago. Streak should die.
        sample_user.streak_days = 10
        sample_user.last_login = date.today() - timedelta(days=2)
        mock_repo.get_or_create_profile.return_value = sample_user

        # Act
        service.finalize_session("TestUser")

        # Assert
        saved_profile = mock_repo.save_profile.call_args[0][0]
        assert saved_profile.streak_days == 1  # Reset to 1 (today counts)

    def test_streak_stays_same_if_already_logged_in_today(self, service, mock_repo, sample_user):
        # Arrange
        # User already finished a session today. Don't double count streak.
        sample_user.streak_days = 5
        sample_user.last_login = date.today()
        mock_repo.get_or_create_profile.return_value = sample_user

        # Act
        service.finalize_session("TestUser")

        # Assert
        saved_profile = mock_repo.save_profile.call_args[0][0]
        assert saved_profile.streak_days == 5  # Unchanged


class TestQuizService_StrategyIntegration:

    def test_get_questions_delegates_to_strategy(self, service, mock_repo):
        # Arrange
        user_id = "User1"
        mode = "TestMode"

        # Create a fake strategy and register it
        mock_strategy = Mock(spec=IQuestionStrategy)
        expected_questions = [Mock(spec=Question)]
        mock_strategy.generate.return_value = expected_questions

        # Inject into Registry (Monkeypatching the singleton for this test)
        StrategyRegistry.register(mode, mock_strategy)

        # Act
        questions = service.get_quiz_questions(mode, user_id)

        # Assert
        assert questions == expected_questions
        mock_strategy.generate.assert_called_once_with(user_id, mock_repo)