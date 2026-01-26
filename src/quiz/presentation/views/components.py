import streamlit as st


def apply_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container { padding-top: 2rem !important; }
            .stat-box {
                padding: 10px;
                background-color: #f0f2f6;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            .question-text {
                font-size: 1.2rem;
                font-weight: 600;
                margin-bottom: 1rem;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )
