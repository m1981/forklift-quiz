from typing import Any

import streamlit as st

from src.components.mobile.shared import SHARED_CSS
from src.config import GameConfig

# -----------------------------------------------------------------------------
# 1. COMPONENT DEFINITION (HTML/CSS/JS)
# -----------------------------------------------------------------------------

DASHBOARD_HTML = """
<div class="dashboard-container">
    <!-- Sprint Button -->
    <button class="card sprint-card" id="sprintBtn">
        <div class="icon-box">🚀</div>
        <div class="content">
            <div class="title" id="sprintTitle"></div>
            <div class="subtitle" id="sprintSub"></div>
        </div>
    </button>

    <!-- Category Grid -->
    <div id="grid" class="grid"></div>
</div>
"""

DASHBOARD_CSS = (
    SHARED_CSS
    + """
.dashboard-container { padding: 0 4px; font-family: "Source Sans Pro", sans-serif; }
.card { display: flex; align-items: center; width: 100%; background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; margin-bottom: 12px; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
.card:active { transform: scale(0.98); }
.sprint-card { border: 1px solid #22c55e; background: #f0fdf4; margin-bottom: 24px; }
.icon-box { font-size: 24px; margin-right: 12px; }
.content { flex: 1; overflow: hidden; }
.title { font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 2px; }
.subtitle { font-size: 12px; color: #4b5563; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.grid { display: flex; flex-direction: column; gap: 12px; }
.cat-item { border: 1px solid #e5e7eb; margin-bottom: 0; }
.cat-title { font-size: 15px; font-weight: 600; color: #111827; margin-bottom: 2px; }
.cat-sub { font-size: 12px; color: #6b7280; }
.badge { padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; margin-left: 8px; min-width: 40px; text-align: center; }
.badge-green-light { background-color: #dcfce7; color: #16a34a; }
.badge-green-solid { background-color: #22c55e; color: white; }
"""
)

DASHBOARD_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;
    const sprintBtn = parentElement.querySelector('#sprintBtn');
    const sprintTitle = parentElement.querySelector('#sprintTitle');
    const sprintSub = parentElement.querySelector('#sprintSub');
    const grid = parentElement.querySelector('#grid');

    sprintTitle.textContent = data.sprintLabel;
    sprintSub.textContent = data.sprintSub;

    sprintBtn.onclick = () => {
        setTriggerValue('action', {type: 'SPRINT', payload: null});
    };

    data.categories.forEach(cat => {
        const item = document.createElement('div');
        item.className = 'cat-item card';
        let badgeClass = 'badge-green-light';
        let badgeText = Math.round(cat.progress * 100) + '%';
        let iconHtml = `<div class="icon-box">${cat.icon}</div>`;

        if (cat.progress >= 1.0) {
            badgeClass = 'badge-green-solid';
            badgeText = '100%';
        }
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
    sprint_count = GameConfig.SPRINT_QUESTIONS
    result = _mobile_dashboard_component(
        data={
            "categories": categories,
            "sprintLabel": "Start",
            "sprintSub": f"{sprint_count} losowych pytań • ~15 mins",
        },
        key=key,
        on_action_change=lambda: None,
    )
    return dict(result.action) if result.action is not None else None
