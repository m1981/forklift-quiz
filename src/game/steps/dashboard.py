import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Union

from src.config import Category
from src.game.core import GameContext, GameStep, UIModel
from src.shared.telemetry import Telemetry


@dataclass
class DashboardPayload:
    """
    DTO containing pre-calculated data for the Dashboard View.
    The View should not need to do any math on this data.
    """

    global_progress: float
    total_mastered: int
    total_questions: int
    finish_date_str: str
    days_left: int
    categories: list[dict[str, Any]]


class DashboardStep(GameStep):
    """
    Prepares the data for the Dashboard screen.
    Acts as a Controller/Presenter for the Dashboard.
    """

    def __init__(self) -> None:
        super().__init__()
        self.telemetry = Telemetry("DashboardStep")

    def enter(self, context: GameContext) -> None:
        super().enter(context)
        # Clear any previous session data when returning to dashboard
        if "score" in context.data:
            del context.data["score"]
        if "errors" in context.data:
            del context.data["errors"]

    def get_ui_model(self) -> UIModel:
        if not self.context:
            raise RuntimeError("DashboardStep accessed before enter()")

        # 1. Fetch Data (Infrastructure)
        # Returns: [{'category': 'BHP', 'total': 10, 'mastered': 5}, ...]
        stats = self.context.repo.get_category_stats(self.context.user_id)

        # 2. Calculate Global Stats (Domain Logic)
        # We explicitly cast to int because we know 'total' and 'mastered' are ints,
        # even though the dict type hint says int | str.
        total_q = sum(int(s["total"]) for s in stats)
        total_mastered = sum(int(s["mastered"]) for s in stats)
        remaining = total_q - total_mastered

        # Logic: 15 questions per day goal
        days_left = math.ceil(remaining / 15) if remaining > 0 else 0
        finish_date = date.today() + timedelta(days=days_left)

        # Avoid division by zero
        global_progress = (total_mastered / total_q) if total_q > 0 else 0.0

        # 3. Prepare Category Data (Presentation Logic)
        cat_data = []
        for stat in stats:
            # Extract and cast for safety
            cat_name = str(stat["category"])
            cat_total = int(stat["total"])
            cat_mastered = int(stat["mastered"])

            cat_data.append(
                {
                    "name": cat_name,
                    "progress": cat_mastered / cat_total if cat_total > 0 else 0,
                    "icon": Category.get_icon(cat_name),
                }
            )

        payload = DashboardPayload(
            global_progress=global_progress,
            total_mastered=total_mastered,
            total_questions=total_q,
            finish_date_str=finish_date.strftime("%d %b"),
            days_left=days_left,
            categories=cat_data,
        )

        return UIModel(type="DASHBOARD", payload=payload)

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        # The Director/ViewModel handles the actual flow switching (START_SPRINT, etc.)
        # based on the action string. The Step itself doesn't need to do much here
        # unless we had internal dashboard states (like tabs).
        return None
