from datetime import date, timedelta
from unittest.mock import Mock

from src.game.core import GameContext
from src.game.steps.dashboard import DashboardStep


def test_dashboard_calculates_dates_correctly():
    # Arrange
    step = DashboardStep()
    mock_repo = Mock()

    # Scenario:
    # Cat A: 10 total, 5 mastered
    # Cat B: 20 total, 0 mastered
    # Total: 30 questions, 5 mastered. Remaining: 25.
    # Daily Goal: 15 (hardcoded in logic for now).
    # Days left: ceil(25 / 15) = 2 days.
    mock_repo.get_category_stats.return_value = [
        {"category": "A", "total": 10, "mastered": 5},
        {"category": "B", "total": 20, "mastered": 0},
    ]

    context = GameContext(user_id="User", repo=mock_repo)
    step.enter(context)

    # Act
    ui_model = step.get_ui_model()
    payload = ui_model.payload

    # Assert
    assert payload.total_questions == 30
    assert payload.total_mastered == 5
    assert payload.days_left == 2

    expected_date = (date.today() + timedelta(days=2)).strftime("%d %b")
    assert payload.finish_date_str == expected_date

    # Check global progress (5/30 = 0.1666...)
    assert abs(payload.global_progress - 0.1666) < 0.01
