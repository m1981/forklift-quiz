import streamlit as st

from src.components.mobile.shared import SHARED_CSS

HERO_HTML = """
<div class="hero-container">
    <div class="header-row">
        <div class="title">Kurs 2 WJO</div>
        <!-- MENU BUTTON -->
        <button id="menuBtn" class="menu-btn">☰</button>
    </div>

    <div class="progress-section">
        <div class="progress-label">
            <span>Globalne Opanowanie</span>
            <span id="global-percent">0%</span>
        </div>
        <div class="progress-bg">
            <div class="progress-fill" id="global-bar"></div>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-box">
            <div class="stat-label">Opanowane</div>
            <div class="stat-value" id="stat-mastered">0 / 0</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Przewidywany Koniec</div>
            <div class="stat-value" id="stat-date">--</div>
            <div class="stat-sub" id="stat-days">--</div>
        </div>
    </div>
</div>
"""

HERO_CSS = (
    SHARED_CSS
    + """
.hero-container {
    padding: 0 4px 16px 4px;
    font-family: "Source Sans Pro", sans-serif;
    color: #31333F;
}

/* --- TITLE --- */
.header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}

.title {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.5px;
}

/* MENU BUTTON */
.menu-btn {
    background: transparent;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #31333F;
    padding: 4px;
    line-height: 1;
}
.menu-btn:active {
    opacity: 0.5;
}

/* --- PROGRESS --- */
.progress-section {
    margin-bottom: 20px;
}

.progress-label {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #555;
    margin-bottom: 6px;
    font-weight: 600;
}

.progress-bg {
    height: 8px;
    background: #f0f2f6;
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #22c55e, #16a34a);
    width: 0%;
    transition: width 1s ease-out;
    border-radius: 4px;
}

/* --- STATS GRID --- */
.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}

.stat-box {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}

.stat-label {
    font-size: 11px;
    text-transform: uppercase;
    color: #9ca3af;
    font-weight: 700;
    margin-bottom: 4px;
    letter-spacing: 0.5px;
}

.stat-value {
    font-size: 20px;
    font-weight: 700;
    color: #1f2937;
}

.stat-sub {
    font-size: 12px;
    color: #22c55e; /* Green */
    font-weight: 600;
    margin-top: 2px;
}
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
    const daysEl = parentElement.querySelector('#stat-days');
    const menuBtn = parentElement.querySelector('#menuBtn');

    // Data
    const pct = Math.round(data.progress * 100);

    // Update DOM
    percentEl.textContent = pct + "%";
    barEl.style.width = pct + "%";

    masteredEl.textContent = `${data.mastered} / ${data.total}`;
    dateEl.textContent = data.finishDate;

    if (data.daysLeft > 0) {
        daysEl.textContent = `za ${data.daysLeft} dni`;
        daysEl.style.color = "#22c55e"; // Green
    } else {
        daysEl.textContent = "Gotowe!";
        daysEl.style.color = "#3b82f6"; // Blue
    }

    // --- MENU CLICK HANDLER ---
    menuBtn.onclick = () => {
        const doc = window.parent.document;
        const sidebarBtn = doc.querySelector(
            'button[data-testid="stExpandSidebarButton"]'
        );
        if (sidebarBtn) {
            sidebarBtn.click();
        } else {
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
    """
    Renders the Dashboard Hero section (Title + Stats).
    """
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
