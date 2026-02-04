import base64
import math
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Union

from src.config import Category, GameConfig
from src.game.core import GameContext, GameStep, UIModel
from src.shared.telemetry import Telemetry


@dataclass
class DashboardPayload:
    app_title: str
    app_logo_src: str
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

    def _get_logo_base64(self) -> str:
        """
        Reads the logo file from config and converts to Base64 Data URI.
        """
        path = GameConfig.APP_LOGO_PATH

        # 1. Check if it's a web URL (pass through)
        if path.startswith("http"):
            return path

        # 2. Check local file
        if os.path.exists(path):
            try:
                with open(path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                    # Determine mime type
                    mime = "image/png"
                    if path.lower().endswith(".jpg") or path.lower().endswith(".jpeg"):
                        mime = "image/jpeg"
                    elif path.lower().endswith(".svg"):
                        mime = "image/svg+xml"

                    return f"data:{mime};base64,{b64_data}"
            except Exception as e:
                self.telemetry.log_error("Failed to load logo", e)

        # 3. Fallback (Transparent pixel)
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

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

        # 1. Fetch Data
        stats = self.context.repo.get_category_stats(self.context.user_id)

        # 2. Calculate Global Stats
        total_q = sum(int(s["total"]) for s in stats)
        total_mastered = sum(int(s["mastered"]) for s in stats)
        remaining = total_q - total_mastered

        throughput = GameConfig.SPRINT_QUESTIONS
        days_left = math.ceil(remaining / throughput) if remaining > 0 else 0

        finish_date = date.today() + timedelta(days=days_left)
        global_progress = (total_mastered / total_q) if total_q > 0 else 0.0

        # 3. Prepare Category Data
        cat_data = []
        for stat in stats:
            full_name = str(stat["category"])
            c_total = int(stat["total"])
            c_mastered = int(stat["mastered"])
            c_icon = Category.get_icon(full_name)

            display_name = full_name
            if len(display_name) > 30:
                display_name = display_name[:28] + "..."

            item = {
                "id": full_name,
                "name": display_name,
                "progress": c_mastered / c_total if c_total > 0 else 0,
                "icon": c_icon,
                "subtitle": f"{c_mastered} / {c_total} Zrobione",
            }
            cat_data.append(item)

        # --- TELEMETRY ---
        self.telemetry.log_info(
            f"Dashboard Stats Calculated: Mastered={total_mastered}/{total_q}",
            categories=[c["name"] for c in cat_data],
        )
        # ----------------------------

        payload = DashboardPayload(
            app_title=GameConfig.APP_TITLE,
            app_logo_src=self._get_logo_base64(),
            global_progress=global_progress,
            total_mastered=total_mastered,
            total_questions=total_q,
            finish_date_str=finish_date.strftime("%d %b"),
            days_left=days_left,
            categories=cat_data,
        )

        # --- DEMO MODE LOGIC ---
        branding_logo = None
        if self.context.is_demo_mode:
            # Resolve the specific logo for this prospect
            branding_logo = GameConfig.get_demo_logo_path(self.context.prospect_slug)
        # -----------------------

        return UIModel(
            type="DASHBOARD",
            payload=payload,
            branding_logo_path=branding_logo,  # <--- Pass to Renderer
        )

    def handle_action(
        self, action: str, payload: Any, context: GameContext
    ) -> Union["GameStep", str, None]:
        return None
