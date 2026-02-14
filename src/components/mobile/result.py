import streamlit as st

from src.components.mobile.shared import SHARED_CSS

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
    margin-bottom: 0px;
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
    font-size: 16px;
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
