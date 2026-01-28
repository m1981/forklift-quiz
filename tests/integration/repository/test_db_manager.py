import os

from src.quiz.adapters.db_manager import DatabaseManager


def test_init_schema_creates_tables(tmp_path):
    """
    GIVEN a path to a non-existent DB
    WHEN DatabaseManager is initialized
    THEN it should create the file and the tables.
    """
    # Arrange
    db_path = tmp_path / "test_quiz.db"
    assert not os.path.exists(db_path)

    # Act
    manager = DatabaseManager(str(db_path))
    conn = manager.get_connection()

    # Assert
    # Check if tables exist
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='questions';"
    )
    assert cursor.fetchone() is not None

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_progress';"
    )
    assert cursor.fetchone() is not None

    manager.close()
