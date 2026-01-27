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
