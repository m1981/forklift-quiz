import streamlit as st

from src.components.mobile.shared import SHARED_CSS

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
    <!-- MENU BUTTON -->
    <button id="menuBtn" class="menu-btn-small">⋮</button>
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
    padding: 2px 0;
}
.home-btn {
    background: #f0f2f6;
    border: none;
    border-radius: 8px;
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

/* SMALL MENU BTN */
.menu-btn-small {
    background: transparent;
    border: none;
    font-size: 20px;
    width: 24px;
    cursor: pointer;
    color: #808495;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.menu-btn-small:active { opacity: 0.5; }
"""
)

HEADER_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    const contextEl = parentElement.querySelector('#context');
    const percentEl = parentElement.querySelector('#percent');
    const barFill = parentElement.querySelector('#barFill');
    const homeBtn = parentElement.querySelector('#homeBtn');
    const menuBtn = parentElement.querySelector('#menuBtn');

    // Populate
    contextEl.textContent = data.context;
    const pct = Math.round(data.progress * 100);
    percentEl.textContent = pct + "%";
    barFill.style.width = pct + "%";

    // Home Click
    homeBtn.onclick = () => {
        setTriggerValue('home_clicked', true);
    };

    // Menu Click (Sidebar Trigger)
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

_mobile_header_component = st.components.v2.component(
    "mobile_header", html=HEADER_HTML, css=HEADER_CSS, js=HEADER_JS, isolate_styles=True
)


def mobile_header(context: str, progress: float, key: str | None = None) -> bool:
    """
    Renders the header. Returns True if Home was clicked.
    """
    result = _mobile_header_component(
        data={"context": context, "progress": progress},
        key=key,
        on_home_clicked_change=lambda: None,
    )
    return result.home_clicked is True
