import logging
import sys

import streamlit as st

from src.config import GameConfig
from src.quiz.presentation.renderer import StreamlitRenderer
from src.quiz.presentation.viewmodel import GameViewModel

# --- 1. Configure Global Logging to Console ---
# Note: We configure this after imports to ensure all modules use this config,
# but imports are moved up to satisfy PEP8 (E402).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,  # Force override of any existing config
)

# Setup
st.set_page_config(page_title="Warehouse Game", layout="centered")
vm = GameViewModel()
renderer = StreamlitRenderer()

# --- Sidebar Menu ---
st.sidebar.header("Menu Główne")

# 1. Daily Sprint (Primary Action)
if st.sidebar.button("🚀 Codzienny Sprint", type="primary", use_container_width=True):
    vm.start_daily_sprint()

st.sidebar.markdown("---")

# 2. Category Selection (Secondary Action)
st.sidebar.subheader("📚 Trening Tematyczny")
selected_cat = st.sidebar.selectbox("Wybierz kategorię:", GameConfig.CATEGORIES)

if st.sidebar.button("Rozpocznij Trening", use_container_width=True):
    vm.start_category_mode(selected_cat)

st.sidebar.markdown("---")

# 3. Admin / Debug
with st.sidebar.expander("⚙️ Opcje"):
    if st.button("Resetuj Szkolenie (Onboarding)"):
        vm.start_onboarding()

# Main Render Loop
ui_data = vm.ui_model
renderer.render(ui_data, vm.handle_ui_action)
