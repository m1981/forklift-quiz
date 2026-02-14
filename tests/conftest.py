import pytest
import streamlit as st

from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.domain.models import OptionKey, Question


class MockSessionState(dict):
    """
    Mock for st.session_state that behaves like both a dict and an object.
    Allows both dict-style and attribute-style access.
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as err:
            raise AttributeError(
                f"'MockSessionState' object has no attribute '{name}'"
            ) from err

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError as err:
            raise AttributeError(
                f"'MockSessionState' object has no attribute '{name}'"
            ) from err


@pytest.fixture(autouse=True)
def mock_streamlit_session():
    """
    Auto-use fixture that ensures st.session_state exists for all tests.
    Uses a custom MockSessionState that supports both dict and attribute access.
    """
    original_session_state = getattr(st, "session_state", None)

    # Replace with our mock
    st.session_state = MockSessionState()

    yield st.session_state

    # Cleanup
    st.session_state.clear()

    # Restore original if it existed
    if original_session_state is not None:
        st.session_state = original_session_state


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
        explanation="SOLID principles",
    )


@pytest.fixture
def sample_user_id():
    return "test_user"


@pytest.fixture
def in_memory_repo():
    """Returns a clean, empty in-memory repository."""
    db_manager = DatabaseManager(db_path=":memory:")
    repo = SQLiteQuizRepository(db_manager=db_manager)
    yield repo
    db_manager.close()


@pytest.fixture
def populated_repo(in_memory_repo, sample_question):
    """Returns a repo pre-filled with one sample question."""
    in_memory_repo.seed_questions([sample_question])
    return in_memory_repo
