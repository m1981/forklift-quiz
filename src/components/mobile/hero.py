import streamlit as st

from src.components.mobile.shared import SHARED_CSS

HERO_HTML = """
<div class="hero-card">
    <div class="header-row">
        <span class="label">GLOBAL MASTERY</span>
    </div>

    <div class="main-stat">
        <span id="global-percent">0%</span>
    </div>

    <div class="progress-bg">
        <div class="progress-fill" id="global-bar"></div>
    </div>

    <div class="stats-grid">
        <div class="stat-item border-right">
            <div class="stat-label">Mastered</div>
            <div class="stat-value" id="stat-mastered">0 / 0</div>
        </div>
        <div class="stat-item">
            <div class="stat-label">Est. Finish</div>
            <div class="stat-value green-text" id="stat-date">--</div>
        </div>
    </div>

    <!-- Menu Button Absolute Positioned inside Card or Relative -->
    <button id="menuBtn" class="menu-btn">⋮</button>
</div>
"""

HERO_CSS = (
    SHARED_CSS
    + """
.hero-card {
    position: relative;
    background: linear-gradient(180deg, #ecfdf5 0%, #ffffff 60%); /* Mint gradient */
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 20px;
    margin: 4px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    font-family: "Source Sans Pro", sans-serif;
    color: #1f2937;
}

.header-row {
    margin-bottom: 8px;
}

.label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    color: #6b7280; /* Gray-500 */
    letter-spacing: 0.5px;
}

.main-stat {
    font-size: 42px;
    font-weight: 700;
    line-height: 1.1;
    color: #111827;
    margin-bottom: 16px;
}

/* --- PROGRESS BAR --- */
.progress-bg {
    height: 10px;
    background: #e5e7eb; /* Gray-200 */
    border-radius: 5px;
    overflow: hidden;
    margin-bottom: 24px;
}

.progress-fill {
    height: 100%;
    background: #22c55e; /* Green-500 */
    width: 0%;
    transition: width 1s ease-out;
    border-radius: 5px;
}

/* --- STATS GRID --- */
.stats-grid {
    display: flex;
    justify-content: space-between;
    border-top: 1px solid #f3f4f6;
    padding-top: 16px;
}

.stat-item {
    flex: 1;
}

.border-right {
    border-right: 1px solid #f3f4f6;
    margin-right: 16px;
}

.stat-label {
    font-size: 12px;
    color: #4b5563; /* Gray-600 */
    margin-bottom: 4px;
}

.stat-value {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
}

.green-text {
    color: #22c55e;
}

/* MENU BUTTON */
.menu-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    background: transparent;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #9ca3af;
    line-height: 1;
}
.menu-btn:hover { color: #4b5563; }
"""
)

HERO_JS = """
export default function(component) {
    const { data, parentElement } = component;

    // Selectors
    const percentEl = parentElement.querySelector('#global-percent');
    const barEl = parentElement.querySelector('#global-bar');
    const masteredEl = parentElement.querySelector('#stat-mastered');
    const dateEl = parentElement.querySelector('#stat-date');
    const menuBtn = parentElement.querySelector('#menuBtn');

    // Data
    const pct = Math.round(data.progress * 100);

    // Update DOM
    percentEl.textContent = pct + "%";
    barEl.style.width = pct + "%";
    masteredEl.textContent = `${data.mastered} / ${data.total}`;
    dateEl.textContent = data.finishDate;

    // Menu Click Handler
    menuBtn.onclick = () => {
        const doc = window.parent.document;
        const sidebarBtn = doc.querySelector(
            'button[data-testid="stExpandSidebarButton"]'
        );
        if (sidebarBtn) sidebarBtn.click();
        else {
            const closeBtn = doc.querySelector(
                'button[data-testid="stCollapseSidebarButton"]'
            );
            if (closeBtn) closeBtn.click();
        }
    };
}
"""

_mobile_hero_component = st.components.v2.component(
    "mobile_hero", html=HERO_HTML, css=HERO_CSS, js=HERO_JS, isolate_styles=True
)


def mobile_hero(
    progress: float,
    mastered_count: int,
    total_count: int,
    finish_date_str: str,
    days_left: int,
    key: str | None = None,
) -> None:
    _mobile_hero_component(
        data={
            "progress": progress,
            "mastered": mastered_count,
            "total": total_count,
            "finishDate": finish_date_str,
            "daysLeft": days_left,
        },
        key=key,
    )
