import streamlit as st

from src.components.mobile.shared import SHARED_CSS

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
    font-family: "Inter";
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
