import pytest

from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.domain.models import OptionKey, Question

# --- Fixtures for Domain Objects ---


@pytest.fixture
def sample_question():
    return Question(
        id="Q1",
        text="What is SOLID?",
        options={
            OptionKey.A: "Liquid",
            OptionKey.B: "Gas",
            OptionKey.C: "Architecture",
            OptionKey.D: "Plasma",
        },
        correct_option=OptionKey.C,
        category="Architecture",
    )


@pytest.fixture
def sample_user_id():
    return "TestUser"


# --- Fixtures for Infrastructure ---


@pytest.fixture
def in_memory_repo():
    """
    Returns a clean, empty in-memory repository.
    Auto-seeding is DISABLED to ensure tests are isolated.
    """
    db_manager = DatabaseManager(db_path=":memory:")
    repo = SQLiteQuizRepository(db_manager=db_manager)
    yield repo
    # Cleanup: Close the database connection
    db_manager.close()


@pytest.fixture
def populated_repo(in_memory_repo, sample_question):
    """
    Returns a repo pre-filled with one sample question.
    """
    in_memory_repo.seed_questions([sample_question])
    return in_memory_repo
