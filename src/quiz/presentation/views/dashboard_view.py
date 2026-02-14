from typing import Any

import streamlit as st

from src.components.mobile import mobile_dashboard, mobile_hero


def render_dashboard_screen(
    service: Any, user_id: str, demo_slug: str | None = None
) -> None:
    # 1. Get Data from Service
    data = service.get_dashboard_stats(user_id, demo_slug)

    # NEW: Check bonus mode
    profile = service.repo.get_or_create_profile(user_id)
    if profile.is_bonus_mode():
        st.success(
            f"🎉 Bonus Mode! Goal reached: {profile.daily_progress}/{profile.daily_goal}"
        )

    # 2. Render Hero Component
    mobile_hero(
        title=data["app_title"],
        logo_src=data["app_logo_src"],
        progress=data["global_progress"],
        mastered_count=data["total_mastered"],
        total_count=data["total_questions"],
        finish_date_str=data["finish_date_str"],
        days_left=data["days_left"],
        key="hero_dash",
    )

    # 3. Render Dashboard Grid Component
    # Returns an action dict: {'type': 'SPRINT', 'payload': ...}
    action = mobile_dashboard(
        categories=data["categories"],
        current_lang=data["preferred_language"],
        key="dash_grid",
    )

    # 4. Handle Actions
    if action:
        if action["type"] == "SPRINT":
            service.start_daily_sprint(user_id)
        elif action["type"] == "CATEGORY":
            service.start_category_mode(user_id, action["payload"])
        elif action["type"] == "LANGUAGE":
            service.update_language(user_id, action["payload"])
            st.rerun()
