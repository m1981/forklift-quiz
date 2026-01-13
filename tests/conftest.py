import pytest
import json
from datetime import date, timedelta
from src.quiz.domain.models import Question, UserProfile, OptionKey
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository

# --- Fixtures for Domain Objects ---

@pytest.fixture
def sample_question():
    return Question(
        id="Q1",
        text="What is SOLID?",
        options={
            OptionKey.A: "Liquid",
            OptionKey.B: "Gas",
            OptionKey.C: "Design Principles",
            OptionKey.D: "Plasma"
        },
        correct_option=OptionKey.C,
        category="Architecture"
    )

@pytest.fixture
def sample_user_id():
    return "test_user_123"

# --- Fixtures for Infrastructure ---

@pytest.fixture
def in_memory_repo():
    repo = SQLiteQuizRepository(db_path=":memory:")
    yield repo
    repo.close() # Clean up the shared connection

@pytest.fixture
def populated_repo(in_memory_repo, sample_question):
    """
    A repo that already has one question seeded.
    """
    in_memory_repo.seed_questions([sample_question])
    return in_memory_repo