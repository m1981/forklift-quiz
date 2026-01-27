from typing import Any

import streamlit as st

from src.components.mobile.shared import SHARED_CSS

DASHBOARD_HTML = """
<div class="dashboard-container">
    <!-- Sprint Button (Pinned Top) -->
    <button class="card sprint-card" id="sprintBtn">
        <div class="icon">🚀</div>
        <div class="content">
            <div class="title">Mix Pytań (Sprint)</div>
            <div class="subtitle">15 losowych pytań</div>
        </div>
        <div class="arrow">➜</div>
    </button>

    <div class="divider">📚 Kategorie</div>

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
}

/* --- SPRINT CARD --- */
.card {
    display: flex;
    align-items: center;
    width: 100%;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    text-align: left;
    transition: transform 0.1s, background 0.1s;
    box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}

.card:active {
    transform: scale(0.98);
    background: #f8f9fa;
}

.sprint-card {
    border: 1px solid #22c55e; /* Green border */
    background: #f0fdf4; /* Very light green bg */
}

.icon {
    font-size: 24px;
    margin-right: 16px;
}

.content {
    flex: 1;
}

.title {
    font-size: 16px;
    font-weight: 600;
    color: #1f2937;
    margin-bottom: 2px;
}

.subtitle {
    font-size: 12px;
    color: #6b7280;
}

.arrow {
    color: #9ca3af;
    font-weight: bold;
}

/* --- DIVIDER --- */
.divider {
    font-size: 13px;
    font-weight: 700;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 20px 0 10px 4px;
}

/* --- GRID LAYOUT --- */
.grid {
    display: grid;
    grid-template-columns: 1fr; /* Mobile: 1 column */
    gap: 10px;
}

/* Desktop Override: 2 Columns if width > 600px */
@media (min-width: 600px) {
    .grid {
        grid-template-columns: 1fr 1fr;
    }
}

/* --- CATEGORY ITEMS --- */
.cat-item {
    display: flex;
    align-items: center;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 12px;
    cursor: pointer;
}

.cat-item:active {
    background: #f9fafb;
    border-color: #d1d5db;
}

.cat-progress {
    font-size: 12px;
    font-weight: 600;
    color: #22c55e; /* Green text for % */
    background: #dcfce7;
    padding: 2px 8px;
    border-radius: 10px;
}
"""
)

DASHBOARD_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    const sprintBtn = parentElement.querySelector('#sprintBtn');
    const grid = parentElement.querySelector('#grid');

    // 1. Handle Sprint Click
    sprintBtn.onclick = () => {
        setTriggerValue('action', {type: 'SPRINT', payload: null});
    };

    // 2. Render Categories
    data.categories.forEach(cat => {
        const item = document.createElement('div');
        item.className = 'cat-item card'; // Reuse card styling
        item.style.marginBottom = '0'; // Grid handles gap

        // Icon Logic
        const isMastered = cat.progress >= 1.0;
        const icon = isMastered ? '✅' : (cat.icon || '📦');
        const pct = Math.round(cat.progress * 100) + '%';

        item.innerHTML = `
            <div class="icon" style="font-size: 20px; margin-right: 12px;">${icon}</div>
            <div class="content">
                <div class="title" style="font-size: 15px;">${cat.name}</div>
            </div>
            <div class="cat-progress">${pct}</div>
        `;

        item.onclick = () => {
            setTriggerValue('action', {type: 'CATEGORY', payload: cat.name});
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
    Renders the full dashboard grid.
    Returns dict: {'type': 'SPRINT'|'CATEGORY', 'payload': ...}
    """
    result = _mobile_dashboard_component(
        data={"categories": categories}, key=key, on_action_change=lambda: None
    )
    action = result.action
    return dict(action) if action is not None else None
