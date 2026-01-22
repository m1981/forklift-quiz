import streamlit as st
import logging
import sys

# --- 1. Configure Global Logging to Console ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True # Force override of any existing config
)

from src.quiz.presentation.viewmodel import GameViewModel
from src.quiz.presentation.renderer import StreamlitRenderer

# Setup
st.set_page_config(page_title="Warehouse Game", layout="centered")
vm = GameViewModel()
renderer = StreamlitRenderer()

# Sidebar (Simplified)
st.sidebar.header("Menu")
if st.sidebar.button("Zacznij Naukę"):
    vm.start_daily_sprint()
if st.sidebar.button("Wprowadzenie"):
    vm.start_onboarding()

# Main Render Loop
ui_data = vm.ui_model
renderer.render(ui_data, vm.handle_ui_action)