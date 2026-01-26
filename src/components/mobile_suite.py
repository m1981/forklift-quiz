from typing import Any

import streamlit as st

# --- 1. SHARED CSS (The "Zero-Waste" Reset) ---
# We use :host to ensure the root container has no extra space
SHARED_CSS = """
:host {
    display: block;
    width: 100%;
    font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont,
                 Roboto, sans-serif;
    box-sizing: border-box;
}
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-tap-highlight-color: transparent;
}
"""

# ==========================================
# COMPONENT 1: MOBILE HEADER (Home + Progress)
# ==========================================

HEADER_HTML = """
<div class="container">
    <button id="homeBtn" class="home-btn">🏠</button>
    <div class="progress-wrapper">
        <div class="meta">
            <span id="context" class="context-text"></span>
            <span id="percent" class="percent-text"></span>
        </div>
        <div class="bar-bg">
            <div id="barFill" class="bar-fill"></div>
        </div>
    </div>
</div>
"""

HEADER_CSS = (
    SHARED_CSS
    + """
.container {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 2px 0; /* Ultra tight padding */
}

.home-btn {
    background: #f0f2f6;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    width: 36px;
    height: 36px;
    font-size: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
}
.home-btn:active { background: #e0e2e6; transform: scale(0.95); }

.progress-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.meta {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #555;
    margin-bottom: 4px;
    font-weight: 600;
}

.bar-bg {
    height: 6px;
    background: #eee;
    border-radius: 3px;
    width: 100%;
    overflow: hidden;
}

.bar-fill {
    height: 100%;
    background: #00cc66;
    width: 0%;
    transition: width 0.4s ease;
}
"""
)

HEADER_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    const contextEl = parentElement.querySelector('#context');
    const percentEl = parentElement.querySelector('#percent');
    const barFill = parentElement.querySelector('#barFill');
    const homeBtn = parentElement.querySelector('#homeBtn');

    // 1. Populate Data
    contextEl.textContent = data.context;
    const pct = Math.round(data.progress * 100);
    percentEl.textContent = pct + "%";
    barFill.style.width = pct + "%";

    // 2. Handle Click
    homeBtn.onclick = () => {
        // DOCS COMPLIANCE: This maps to on_home_clicked_change in Python
        setTriggerValue('home_clicked', true);
    };
}
"""

_mobile_header_component = st.components.v2.component(
    "mobile_header", html=HEADER_HTML, css=HEADER_CSS, js=HEADER_JS, isolate_styles=True
)


def mobile_header(context: str, progress: float, key: str | None = None) -> bool:
    """
    Renders the header. Returns True if Home was clicked.
    """
    # We pass on_home_clicked_change to satisfy the V2 API requirement
    result = _mobile_header_component(
        data={"context": context, "progress": progress},
        key=key,
        on_home_clicked_change=lambda: None,
    )
    return result.home_clicked is True


# ==========================================
# COMPONENT 2: MOBILE OPTION BUTTON
# ==========================================

OPTION_HTML = """
<button id="btn" class="option-card">
    <div id="badge" class="badge">A</div>
    <div id="text" class="text">Option Text</div>
</button>
"""

OPTION_CSS = (
    SHARED_CSS
    + """
.option-card {
    display: flex;
    align-items: flex-start;
    width: 100%;
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 12px;
    margin-bottom: 0px; /* Space between buttons */
    cursor: pointer;
    text-align: left;
    transition: all 0.1s;
    color: #31333F;
}

.option-card:active {
    background-color: #f0f2f6; /* Slightly darker grey */
    border-color: #808495;     /* Neutral Grey instead of Red */
    transform: scale(0.99);
}

.badge {
    background: #f0f2f6;
    color: #31333F;
    font-weight: 700;
    font-size: 13px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 12px;
    flex-shrink: 0;
    margin-top: 1px; /* Optical alignment with text */
}

.text {
    font-size: 15px;
    line-height: 1.4;
    word-wrap: break-word;
}
"""
)

OPTION_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    const btn = parentElement.querySelector('#btn');
    const badge = parentElement.querySelector('#badge');
    const text = parentElement.querySelector('#text');

    // 1. Populate
    badge.textContent = data.key;
    text.textContent = data.text;

    // 2. Click Handler
    btn.onclick = () => {
        // DOCS COMPLIANCE: Maps to on_clicked_change
        setTriggerValue('clicked', data.key);
    };
}
"""

_mobile_option_component = st.components.v2.component(
    "mobile_option", html=OPTION_HTML, css=OPTION_CSS, js=OPTION_JS, isolate_styles=True
)


def mobile_option(key_char: str, text: str, key: str | None = None) -> str | None:
    """
    Renders an option button. Returns the key_char (e.g. 'A') if clicked.
    """
    result = _mobile_option_component(
        data={"key": key_char, "text": text}, key=key, on_clicked_change=lambda: None
    )
    clicked = result.clicked
    return str(clicked) if clicked is not None else None


# ==========================================
# COMPONENT 3: MOBILE RESULT ROW (Read-Only)
# ==========================================

RESULT_HTML = """
<div id="card" class="result-card">
    <div id="badge" class="badge">A</div>
    <div id="text" class="text">Option Text</div>
    <div id="icon" class="status-icon"></div>
</div>
"""

RESULT_CSS = (
    SHARED_CSS
    + """
.result-card {
    display: flex;
    align-items: flex-start;
    width: 100%;
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 12px;
    margin-bottom: 8px;
    text-align: left;
    color: #31333F;
    opacity: 0.8; /* Slightly faded to indicate read-only */
}

/* --- STATES --- */

/* 1. CORRECT (Green) */
.result-card.correct {
    background-color: #ecfdf5; /* Gentle Mint */
    border-color: #10b981;
    opacity: 1;
}
.result-card.correct .badge {
    background-color: #d1fae5;
    color: #065f46;
}

/* 2. WRONG (Red) */
.result-card.wrong {
    background-color: #fef2f2; /* Gentle Rose */
    border-color: #ef4444;
    opacity: 1;
}
.result-card.wrong .badge {
    background-color: #fee2e2;
    color: #991b1b;
}

/* 3. MISSED (The correct answer when you picked wrong) */
.result-card.missed {
    border-color: #10b981;
    border-style: dashed;
    background-color: #f0fdf4;
}

/* --- COMMON ELEMENTS --- */
.badge {
    background: #f0f2f6;
    color: #31333F;
    font-weight: 700;
    font-size: 13px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 12px;
    flex-shrink: 0;
    margin-top: 1px;
}

.text {
    font-size: 15px;
    line-height: 1.4;
    flex: 1; /* Take remaining space */
}

.status-icon {
    font-size: 16px;
    margin-left: 8px;
}
"""
)

RESULT_JS = """
export default function(component) {
    const { data, parentElement } = component;

    const card = parentElement.querySelector('#card');
    const badge = parentElement.querySelector('#badge');
    const text = parentElement.querySelector('#text');
    const icon = parentElement.querySelector('#icon');

    // Populate
    badge.textContent = data.key;
    text.textContent = data.text;

    // Apply State Styling
    if (data.state === 'correct') {
        card.classList.add('correct');
        icon.textContent = '✅';
    } else if (data.state === 'wrong') {
        card.classList.add('wrong');
        icon.textContent = '❌';
    } else if (data.state === 'missed') {
        card.classList.add('missed');
        icon.textContent = '👈'; // Gentle pointer
    } else {
        // Neutral
        icon.textContent = '';
    }
}
"""

_mobile_result_component = st.components.v2.component(
    "mobile_result", html=RESULT_HTML, css=RESULT_CSS, js=RESULT_JS, isolate_styles=True
)


def mobile_result_row(
    key_char: str, text: str, state: str = "neutral", key: str | None = None
) -> None:
    """
    Renders a read-only result row.
    state: 'correct', 'wrong', 'missed', 'neutral'
    """
    _mobile_result_component(
        data={"key": key_char, "text": text, "state": state}, key=key
    )


# ==========================================
# COMPONENT 4: MOBILE DASHBOARD GRID
# ==========================================

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
