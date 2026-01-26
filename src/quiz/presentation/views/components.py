# src/quiz/presentation/views/components.py

import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
            /* 1. HIDE STREAMLIT HEADER/TOOLBAR */
            header[data-testid="stHeader"] {
                visibility: hidden;
                height: 0px;
            }

            /* 2. HIDE THE COLORED DECORATION BAR AT TOP */
            div[data-testid="stDecoration"] {
                visibility: hidden;
                height: 0px;
            }

            /* 3. ADJUST TOP PADDING TO RECLAIM SPACE */
            /* The block-container is the main wrapper. We pull it up. */
            .block-container {
                padding-top: 0rem !important; /* Was 1rem or 6rem */
                padding-bottom: 1rem !important;
            }

            /* 4. HIDE FOOTER (Optional, "Made with Streamlit") */
            footer {
                visibility: hidden;
                height: 0px;
            }

            /* ... (Keep your existing button styles below) ... */
            div[data-testid="stButton"] > button {
                /* ... your existing button CSS ... */
            }
        </style>
    """,
        unsafe_allow_html=True,
    )
