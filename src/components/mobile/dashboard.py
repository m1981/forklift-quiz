import base64
import math
import os
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Union

import streamlit as st

from src.components.mobile.shared import SHARED_CSS
from src.config import Category, GameConfig
from src.game.core import GameContext, GameStep, UIModel
from src.shared.telemetry import Telemetry

# -----------------------------------------------------------------------------
# 1. COMPONENT DEFINITION (HTML/CSS/JS)
# -----------------------------------------------------------------------------

DASHBOARD_HTML = """
<div class="dashboard-container">
    <!-- Sprint Button -->
    <button class="card sprint-card" id="sprintBtn">
        <div class="icon-box">🚀</div>
        <div class="content">
            <!-- Text injected via JS from Python Data -->
            <div class="title" id="sprintTitle"></div>
            <div class="subtitle" id="sprintSub"></div>
        </div>
    </button>

    <!-- Category Grid -->
    <div id="grid" class="grid">
        <!-- Items injected via JS -->
    </div>
</div>
"""

DASHBOARD_CSS = (
    SHARED_CSS
    + """
.dashboard-container {
    padding: 0 4px;
    font-family: "Source Sans Pro", sans-serif;
}

/* --- CARDS (Generic) --- */
.card {
    display: flex;
    align-items: center;
    width: 100%;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    text-align: left;
    transition: transform 0.1s, background 0.1s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.card:active {
    transform: scale(0.98);
}

/* --- SPRINT CARD SPECIFIC --- */
.sprint-card {
    border: 1px solid #22c55e; /* Green border */
    background: #f0fdf4; /* Light Green BG */
    margin-bottom: 24px; /* More space before categories */
}

.icon-box {
    font-size: 24px;
    margin-right: 12px;
}

.content {
    flex: 1;
    overflow: hidden; /* For text ellipsis */
}

.title {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 2px;
}

.subtitle {
    font-size: 12px;
    color: #4b5563;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* --- GRID --- */
.grid {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

/* --- CATEGORY ITEM --- */
.cat-item {
    border: 1px solid #e5e7eb;
    margin-bottom: 0; /* Reset generic card margin */
}

.cat-title {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    margin-bottom: 2px;
}

.cat-sub {
    font-size: 12px;
    color: #6b7280;
}

/* --- BADGES --- */
.badge {
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    margin-left: 8px;
    min-width: 40px;
    text-align: center;
}

.badge-green-light {
    background-color: #dcfce7; /* Light Green */
    color: #16a34a; /* Dark Green Text */
}

.badge-green-solid {
    background-color: #22c55e; /* Solid Green */
    color: white;
}
"""
)

DASHBOARD_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    // --- DEBUGGING: Log what Python sent us ---
    console.log("DASHBOARD COMPONENT RECEIVED DATA:", data);
    if (data.categories && data.categories.length > 0) {
        console.log("First Category Item:", data.categories[0]);
    }
    // ------------------------------------------

    const sprintBtn = parentElement.querySelector('#sprintBtn');
    const sprintTitle = parentElement.querySelector('#sprintTitle');
    const sprintSub = parentElement.querySelector('#sprintSub');
    const grid = parentElement.querySelector('#grid');

    // 1. Populate Sprint Button Text (Dynamic)
    sprintTitle.textContent = data.sprintLabel;
    sprintSub.textContent = data.sprintSub;

    // 2. Sprint Click
    sprintBtn.onclick = () => {
        setTriggerValue('action', {type: 'SPRINT', payload: null});
    };

    // 2. Render Categories
    data.categories.forEach(cat => {
        const item = document.createElement('div');
        item.className = 'cat-item card';

        // Badge Logic
        let badgeClass = 'badge-green-light';
        let badgeText = Math.round(cat.progress * 100) + '%';
        let iconHtml = `<div class="icon-box">${cat.icon}</div>`;

        if (cat.progress >= 1.0) {
            badgeClass = 'badge-green-solid';
            badgeText = '100%';
        }

        // CHECK FOR MISSING SUBTITLE
        const subText = cat.subtitle ? cat.subtitle : "MISSING DATA";

        item.innerHTML = `
            ${iconHtml}
            <div class="content">
                <div class="cat-title">${cat.name}</div>
                <div class="cat-sub">${subText}</div>
            </div>
            <div class="badge ${badgeClass}">${badgeText}</div>
        `;

        item.onclick = () => {
            // CRITICAL: Use cat.id (Full Name) for logic, fallback to cat.name
            const payloadId = cat.id || cat.name;
            setTriggerValue('action', {type: 'CATEGORY', payload: payloadId});
        };

        grid.appendChild(item);
    });
}
"""

_mobile_dashboard_component = st.components.v2.component(
    "mobile_dashboard",
    html=DASHBOARD_HTML,
    css=DASHBOARD_CSS,
    js=DASHBOARD_JS,
    isolate_styles=True,
)


def mobile_dashboard(
    categories: list[dict[str, Any]], key: str | None = None
) -> dict[str, Any] | None:
    """
    Renders the dashboard grid.
    Returns: {'type': 'SPRINT'|'CATEGORY', 'payload': ...}
    """
    # Prepare dynamic text based on GameConfig
    sprint_count = GameConfig.SPRINT_QUESTIONS

    result = _mobile_dashboard_component(
        data={
            "categories": categories,
            "sprintLabel": "Start Daily Sprint",
            "sprintSub": f"{sprint_count} Random Questions • ~3 mins",
        },
        key=key,
        on_action_change=lambda: None,
    )
    return dict(result.action) if result.action is not None else None


# -----------------------------------------------------------------------------
# 2. BUSINESS LOGIC (CONTROLLER)
# -----------------------------------------------------------------------------


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
    def __init__(self) -> None:
        super().__init__()
        self.telemetry = Telemetry("DashboardStep")

    def enter(self, context: GameContext) -> None:
        super().enter(context)
        if "score" in context.data:
            del context.data["score"]
        if "errors" in context.data:
            del context.data["errors"]

    def get_ui_model(self) -> UIModel:
        if not self.context:
            raise RuntimeError("No Context")

        stats = self.context.repo.get_category_stats(self.context.user_id)

        total_q = sum(int(s["total"]) for s in stats)
        total_mastered = sum(int(s["mastered"]) for s in stats)
        remaining = total_q - total_mastered

        # Use Config for throughput estimate
        throughput = GameConfig.SPRINT_QUESTIONS
        days_left = math.ceil(remaining / throughput) if remaining > 0 else 0

        finish_date = date.today() + timedelta(days=days_left)
        global_progress = (total_mastered / total_q) if total_q > 0 else 0.0

        cat_data = []
        for stat in stats:
            full_name = str(stat["category"])
            c_total = int(stat["total"])
            c_mastered = int(stat["mastered"])
            c_icon = Category.get_icon(full_name)

            # Shorten long name for display
            display_name = full_name
            if len(display_name) > 30:
                display_name = display_name[:28] + "..."

            # Construct the item
            item = {
                "id": full_name,  # Logic ID (Full Name)
                "name": display_name,  # Display Label (Shortened)
                "progress": c_mastered / c_total if c_total > 0 else 0,
                "icon": c_icon,
                "subtitle": f"{c_mastered} / {c_total} Mastered",
            }
            cat_data.append(item)

        # --- TELEMETRY ---
        if cat_data:
            self.telemetry.log_info(f"Dashboard Payload Sample (Item 0): {cat_data[0]}")
        else:
            self.telemetry.log_info("Dashboard Payload is empty!")
        # --------------------------------------------------------

        payload = DashboardPayload(
            app_title=GameConfig.APP_TITLE,
            app_logo_src=self._get_logo_base64(),  # <--- Load Image
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
        return None

    def _get_logo_base64(self) -> str:
        """Reads the logo file from config and converts to Base64 Data URI."""
        path = GameConfig.APP_LOGO_PATH

        if path.startswith("http"):
            return path

        if os.path.exists(path):
            try:
                with open(path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")
                    mime = "image/png"
                    if path.lower().endswith((".jpg", ".jpeg")):
                        mime = "image/jpeg"
                    elif path.lower().endswith(".svg"):
                        mime = "image/svg+xml"
                    return f"data:{mime};base64,{b64_data}"
            except Exception as e:
                self.telemetry.log_error("Failed to load logo", e)

        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
