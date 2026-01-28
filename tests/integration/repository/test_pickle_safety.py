import os
import pickle
from collections.abc import Generator

import pytest

from src.game.core import GameContext
from src.game.director import GameDirector
from src.quiz.adapters.db_manager import DatabaseManager
from src.quiz.adapters.sqlite_repository import SQLiteQuizRepository
from src.quiz.domain.models import OptionKey, Question

# Define a temporary DB path for testing
TEST_DB_PATH = "test_pickle.db"


@pytest.fixture
def db_manager() -> Generator[DatabaseManager, None, None]:
    # Setup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    manager = DatabaseManager(TEST_DB_PATH)
    yield manager

    # Teardown
    manager.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_game_director_is_pickle_safe(db_manager: DatabaseManager) -> None:
    """
    Verifies that the GameDirector (and its dependencies) can be pickled
    and unpickled without crashing due to sqlite3.Connection objects.
    """
    # 1. Setup the Object Graph
    repo = SQLiteQuizRepository(db_manager)

    # Seed a question so we can verify DB access later
    q = Question(
        id="Q1", text="Test?", options={OptionKey.A: "A"}, correct_option=OptionKey.A
    )
    repo.seed_questions([q])

    context = GameContext(user_id="test_user", repo=repo)
    director = GameDirector(context)

    # 2. Verify connection is active before pickle
    assert db_manager._shared_connection is not None

    # 3. ATTEMPT PICKLE (Serialization)
    try:
        serialized_data = pickle.dumps(director)
    except TypeError as e:
        pytest.fail(f"Pickling failed! Likely due to open DB connection: {e}")

    # 4. Simulate Streamlit Rerun (Close old connection)
    db_manager.close()

    # 5. ATTEMPT UNPICKLE (Deserialization)
    restored_director = pickle.loads(serialized_data)

    # 6. Verify State Restoration
    assert isinstance(restored_director, GameDirector)
    assert restored_director.context.user_id == "test_user"

    # 7. CRITICAL: Verify DB Reconnection
    # The restored manager should have _shared_connection = None initially
    restored_manager = restored_director.context.repo.db_manager  # type: ignore[attr-defined]
    assert restored_manager._shared_connection is None

    # But calling a repo method should trigger lazy reconnection
    questions = restored_director.context.repo.get_questions_by_ids(["Q1"])

    assert len(questions) == 1
    assert questions[0].id == "Q1"
    assert restored_manager._shared_connection is not None  # Should be active now


def test_telemetry_is_pickle_safe() -> None:
    """
    Ensures the Telemetry class (used everywhere) doesn't break pickling
    due to logging.Logger objects.
    """
    from src.shared.telemetry import Telemetry

    t = Telemetry("TestComponent")
    t.log_info("Before pickle")

    dump = pickle.dumps(t)
    restored_t = pickle.loads(dump)

    # Should be able to log again without crashing
    restored_t.log_info("After pickle")
    assert restored_t.component == "TestComponent"
