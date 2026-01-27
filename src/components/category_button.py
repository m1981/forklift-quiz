import streamlit as st

HTML = """
<button class="card-button" type="button">
    <div class="left-content">
        <span class="icon"></span>
        <div class="text-content">
            <div class="title"></div>
            <div class="subtitle"></div>
        </div>
    </div>
    <div class="badge"></div>
</button>
"""

CSS = """
.card-button {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 12px 16px;
    margin-bottom: 8px;
    background-color: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s;
    color: #1f2937;
    font-family: "Source Sans Pro", sans-serif;
    text-align: left;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.card-button:active {
    background-color: #f9fafb;
    transform: scale(0.99);
}

.left-content {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-width: 0;
}

.icon {
    font-size: 20px;
}

.text-content {
    display: flex;
    flex-direction: column;
}

.title {
    font-size: 15px;
    font-weight: 600;
    color: #111827;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.subtitle {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
}

.badge {
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    margin-left: 10px;
}

.badge-light {
    background-color: #dcfce7;
    color: #16a34a;
}
.badge-solid {
    background-color: #22c55e;
    color: #ffffff;
}
"""

JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    const button = parentElement.querySelector('.card-button');
    const iconSpan = parentElement.querySelector('.icon');
    const titleDiv = parentElement.querySelector('.title');
    const subtitleDiv = parentElement.querySelector('.subtitle');
    const badgeDiv = parentElement.querySelector('.badge');

    // Populate
    iconSpan.textContent = data.icon;
    titleDiv.textContent = data.label;
    subtitleDiv.textContent = data.subtitle || ''; // New data field

    // Badge Logic
    // We expect 'progress' to be a percentage string like "45%"
    badgeDiv.textContent = data.progress;

    if (data.isMastered) {
        badgeDiv.classList.add('badge-solid');
    } else {
        badgeDiv.classList.add('badge-light');
    }

    // Click
    button.onclick = () => {
        setTriggerValue('clicked', data.id);
    };
}
"""

_category_button_component = st.components.v2.component(
    "category_button", html=HTML, css=CSS, js=JS, isolate_styles=True
)


def category_button(
    id: str,
    label: str,
    subtitle: str = "",
    progress: str = "0%",
    icon: str = "📦",
    isMastered: bool = False,
    key: str | None = None,
) -> str | None:
    """
    Renders a category button.
    """
    component_data = {
        "id": id,
        "label": label,
        "subtitle": subtitle,
        "progress": progress,
        "icon": icon,
        "isMastered": isMastered,
    }

    result = _category_button_component(
        data=component_data, key=key, on_clicked_change=lambda: None
    )

    clicked_value = result.clicked
    return str(clicked_value) if clicked_value is not None else None
