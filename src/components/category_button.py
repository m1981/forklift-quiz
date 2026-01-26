import streamlit as st

# 1. Define the HTML Structure
# We use data attributes (data-label, data-progress) to pass info to JS
HTML = """
<button class="card-button" type="button">
    <div class="left-content">
        <span class="icon"></span>
        <span class="label"></span>
    </div>
    <div class="right-content">
        <span class="progress"></span>
    </div>
</button>
"""

# 2. Define the CSS Styling
# Note: We can use standard CSS here.
CSS = """
.card-button {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0.75rem 1rem;
    margin-bottom: 0.2rem;
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease-in-out;
    color: #31333F;
    font-family: "Source Sans Pro", sans-serif;
    font-size: 1rem;
    line-height: 1.5;
    text-align: left;
    box-sizing: border-box;
}

.card-button:hover {
    border-color: #ff4b4b;
    background-color: #fcfcfc;
    transform: translateX(2px);
}

.card-button.active {
    border-color: #ff4b4b;
    background-color: #fff5f5;
    font-weight: 600;
}

.left-content {
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 0;
}

.label {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.right-content {
    margin-left: 15px;
    color: #808495;
    font-family: monospace;
}
"""

# 3. Define the JavaScript Logic
# This function receives the 'component' object to talk to Streamlit
JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;

    // Select elements
    const button = parentElement.querySelector('.card-button');
    const iconSpan = parentElement.querySelector('.icon');
    const labelSpan = parentElement.querySelector('.label');
    const progressSpan = parentElement.querySelector('.progress');

    // Populate data from Python
    iconSpan.textContent = data.icon;
    labelSpan.textContent = data.label;
    progressSpan.textContent = data.progress;

    // Handle Active State
    if (data.isActive) {
        button.classList.add('active');
    } else {
        button.classList.remove('active');
    }

    // Handle Click
    // We send the 'label' back as a trigger value when clicked
    button.onclick = (e) => {
        setTriggerValue('clicked', data.id);
    };
}
"""

# 4. Register the Component
_category_button_component = st.components.v2.component(
    "category_button",
    html=HTML,
    css=CSS,
    js=JS,
    isolate_styles=True,  # Keep styles inside shadow DOM so they don't break app
)


# 5. Create the Python Wrapper
def category_button(
    id: str,
    label: str,
    progress: str = "0%",
    icon: str = "🔨",
    isActive: bool = False,
    key: str | None = None,
) -> str | None:
    """
    Renders a category button.
    Returns the ID if clicked, otherwise None.
    """

    # Prepare data to send to JS
    component_data = {
        "id": id,
        "label": label,
        "progress": progress,
        "icon": icon,
        "isActive": isActive,
    }

    # Call the component
    # We define 'on_clicked_change' because we setTriggerValue in JS
    result = _category_button_component(
        data=component_data, key=key, on_clicked_change=lambda: None
    )

    # Return the ID if clicked
    clicked_value = result.clicked
    if clicked_value is None:
        return None
    return str(clicked_value)
