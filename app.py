import streamlit as st
from src.quiz.presentation.viewmodel import GameViewModel
from src.quiz.presentation.renderer import StreamlitRenderer

# Setup
st.set_page_config(page_title="Warehouse Game", layout="centered")
vm = GameViewModel()
renderer = StreamlitRenderer()

# Sidebar (Simplified)
st.sidebar.header("Menu")
if st.sidebar.button("Start Daily Sprint"):
    vm.start_daily_sprint()
if st.sidebar.button("Start Onboarding"):
    vm.start_onboarding()

# Main Render Loop
ui_data = vm.ui_model

# We pass 'vm.handle_ui_action' as the callback to the renderer
renderer.render(ui_data, vm.handle_ui_action)