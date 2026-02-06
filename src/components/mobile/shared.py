# --- ADR 007: Inline CSS/JS in Python Components ---
# Decision: We keep HTML/CSS/JS as Python string constants within the
# component modules.
# Rationale: Streamlit Components V2 accepts code as strings. While separating
# them into .css/.js files is possible, it complicates the build/deployment
# process (requires file reading). Keeping them co-located makes the component
# self-contained and easier to distribute as a Python package.
# ---------------------------------------------------

# We use :host to ensure the root container has no extra space
SHARED_CSS = """
/* 1. Import the Font inside the component iframe */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

:host {
    display: block;
    width: 100%;
    /* 2. Apply the font globally to the component */
    font-family: "Inter", -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    box-sizing: border-box;

    /* Optional: Set a base font size for consistency */
    font-size: 16px;
    color: #111827; /* Default text color */
}
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    -webkit-tap-highlight-color: transparent;
}
"""
