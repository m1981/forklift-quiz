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
    background-color: #f8f9fb;
    border-color: #ff4b4b;
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
