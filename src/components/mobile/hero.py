import streamlit as st

from src.components.mobile.shared import SHARED_CSS

HERO_HTML = """
<div class="hero-compact">
    <!-- Left: Logo -->
    <div class="logo-col">
        <div class="logo-box">
            <img id="app-logo-img" src="" alt="Logo" />
        </div>
    </div>

    <!-- Center: Info -->
    <div class="info-col">
        <div class="app-title" id="app-title"></div>

        <div class="progress-row">
            <div class="progress-track">
                <div class="progress-fill" id="global-bar"></div>
            </div>
            <div class="percent-text" id="global-percent">0%</div>
        </div>

        <div class="stats-row">
            <span id="stat-mastered">0/0</span> Zrobione • Koniec: <span id="stat-date" class="highlight">--</span>
        </div>
    </div>

    <!-- Right: Menu -->
    <div class="menu-col">
        <button id="menuBtn" class="menu-btn">⋮</button>
    </div>
</div>
"""

HERO_CSS = (
    SHARED_CSS
    + """
.hero-compact {
    display: flex;
    align-items: center;
    background: white;
    border-bottom: 1px solid #e5e7eb;
    padding: 12px 8px;
    margin: 0 -4px 16px -4px;
    font-family: "Inter", sans-serif;
}

/* --- LOGO --- */
.logo-col {
    margin-right: 12px;
}

.logo-box {
    width: 96px;
    height: 96px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px; /* Padding inside the box */
    overflow: hidden;
}

.logo-box img {
    width: 100%;
    height: 100%;
    object-fit: contain; /* Ensures image fits without distortion */
    display: block;
}

/* --- INFO --- */
.info-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden; /* Prevent text overflow */
}

.app-title {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* --- PROGRESS --- */
.progress-row {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
}

.progress-track {
    flex: 1;
    height: 6px;
    background: #e5e7eb;
    border-radius: 3px;
    overflow: hidden;
    margin-right: 8px;
}

.progress-fill {
    height: 100%;
    background: #22c55e; /* Green-500 */
    width: 0%;
    transition: width 0.5s ease-out;
    border-radius: 3px;
}

.percent-text {
    font-size: 16px;
    font-weight: 700;
    color: #374151;
    min-width: 32px;
    text-align: right;
}

/* --- STATS --- */
.stats-row {
    font-size: 16px;
    color: #6b7280;
}

.highlight {
    color: #16a34a; /* Green-600 */
    font-weight: 600;
}

/* --- MENU --- */
.menu-col {
    margin-left: 4px;
    align-self: flex-start;
}

.menu-btn {
    background: transparent;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #9ca3af;
    padding: 0 8px;
    line-height: 1;
}
.menu-btn:hover { color: #4b5563; }
"""
)

HERO_JS = """
export default function(component) {
    const { data, parentElement } = component;

    // Selectors
    const imgEl = parentElement.querySelector('#app-logo-img');
    const titleEl = parentElement.querySelector('#app-title');
    const barEl = parentElement.querySelector('#global-bar');
    const percentEl = parentElement.querySelector('#global-percent');
    const masteredEl = parentElement.querySelector('#stat-mastered');
    const dateEl = parentElement.querySelector('#stat-date');
    const menuBtn = parentElement.querySelector('#menuBtn');

    // Data Binding
    if (data.logoSrc) {
        imgEl.src = data.logoSrc;
    }

    titleEl.textContent = data.title;

    const pct = Math.round(data.progress * 100);
    barEl.style.width = pct + "%";
    percentEl.textContent = pct + "%";

    masteredEl.textContent = `${data.mastered}/${data.total}`;
    dateEl.textContent = data.finishDate;

    // Menu Action
    menuBtn.onclick = () => {
        const doc = window.parent.document;
        // Try to find Streamlit sidebar toggle
        const sidebarBtn = doc.querySelector('button[data-testid="stExpandSidebarButton"]');
        if (sidebarBtn) {
            sidebarBtn.click();
        } else {
            const closeBtn = doc.querySelector('button[data-testid="stCollapseSidebarButton"]');
            if (closeBtn) closeBtn.click();
        }
    };
}
"""

_mobile_hero_component = st.components.v2.component(
    "mobile_hero", html=HERO_HTML, css=HERO_CSS, js=HERO_JS, isolate_styles=True
)


def mobile_hero(
    title: str,
    logo_src: str,
    progress: float,
    mastered_count: int,
    total_count: int,
    finish_date_str: str,
    days_left: int,
    key: str | None = None,
) -> None:
    """
    Renders the compact header with logo, title, and progress.
    """
    _mobile_hero_component(
        data={
            "title": title,
            "logoSrc": logo_src,
            "progress": progress,
            "mastered": mastered_count,
            "total": total_count,
            "finishDate": finish_date_str,
            "daysLeft": days_left,
        },
        key=key,
    )
