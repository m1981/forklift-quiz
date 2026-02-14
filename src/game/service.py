import math
from datetime import date, timedelta
from typing import Any

import streamlit as st

from src.config import Category, GameConfig
from src.quiz.domain.models import Language, Question
from src.quiz.domain.ports import IQuizRepository
from src.quiz.domain.spaced_repetition import SpacedRepetitionSelector


class GameService:
    def __init__(self, repo: IQuizRepository):
        self.repo = repo
        self.selector = SpacedRepetitionSelector()

    # --- Session Management ---

    def _reset_quiz_state(self, questions: list[Question], title: str) -> None:
        """Resets session state variables for a new quiz."""
        st.session_state.quiz_questions = questions
        st.session_state.quiz_title = title
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.answers_history = []  # List[bool]
        st.session_state.screen = "quiz"
        st.session_state.feedback_mode = False
        st.session_state.last_feedback = None
        st.session_state.quiz_errors = []  # Track IDs of failed questions

    # --- Dashboard Logic ---

    def get_dashboard_stats(
        self, user_id: str, demo_slug: str | None = None
    ) -> dict[str, Any]:
        """Calculates all data needed for the Dashboard view."""
        stats = self.repo.get_category_stats(user_id)
        profile = self.repo.get_or_create_profile(user_id)

        total_q = sum(int(s["total"]) for s in stats)
        total_mastered = sum(int(s["mastered"]) for s in stats)
        remaining = total_q - total_mastered

        throughput = GameConfig.SPRINT_QUESTIONS
        days_left = math.ceil(remaining / throughput) if remaining > 0 else 0
        finish_date = date.today() + timedelta(days=days_left)
        global_progress = (total_mastered / total_q) if total_q > 0 else 0.0

        # Prepare Category Data for UI
        cat_data = []
        for stat in stats:
            full_name = str(stat["category"])
            c_total = int(stat["total"])
            c_mastered = int(stat["mastered"])
            c_icon = Category.get_icon(full_name)
            display_name = full_name
            if len(display_name) > 30:
                display_name = display_name[:28] + "..."

            cat_data.append(
                {
                    "id": full_name,
                    "name": display_name,
                    "progress": c_mastered / c_total if c_total > 0 else 0,
                    "icon": c_icon,
                    "subtitle": f"{c_mastered} / {c_total} Zrobione",
                }
            )
        # Determine which logo to show
        if demo_slug:
            logo_path = GameConfig.get_demo_logo_path(demo_slug)
        else:
            logo_path = GameConfig.APP_LOGO_PATH

        logo_b64 = GameConfig.get_image_base64(logo_path)
        # --- FIX END ---

        return {
            "app_title": GameConfig.APP_TITLE,
            "app_logo_src": logo_b64,  # <--- Use the resolved variable
            "global_progress": global_progress,
            "total_mastered": total_mastered,
            "total_questions": total_q,
            "finish_date_str": finish_date.strftime("%d %b"),
            "days_left": days_left,
            "categories": cat_data,
            "preferred_language": profile.preferred_language.value,
        }

    # --- Game Actions ---

    def start_daily_sprint(self, user_id: str) -> None:
        candidates = self.repo.get_repetition_candidates(user_id)
        questions = self.selector.select(candidates, limit=GameConfig.SPRINT_QUESTIONS)

        if not questions:
            st.toast("🎉 Wszystko opanowane! Wróć jutro.", icon="🏆")
            return

        self._reset_quiz_state(questions, "🚀 Codzienny Sprint")
        st.rerun()

    def start_category_mode(self, user_id: str, category: str) -> None:
        questions = self.repo.get_questions_by_category(
            category, user_id, limit=GameConfig.SPRINT_QUESTIONS
        )

        if not questions:
            st.toast(f"Brak pytań w kategorii: {category}", icon="📭")
            return

        self._reset_quiz_state(questions, f"📚 {category}")
        st.rerun()

    def start_onboarding(self, user_id: str) -> None:
        # Create a dummy tutorial question
        from src.quiz.domain.models import OptionKey

        tutorial_q = Question(
            id="TUT-01",
            text="To jest pytanie treningowe. Gdzie składować materiały łatwopalne?",
            options={
                OptionKey.A: "W strefie bezpiecznej (Zielona)",
                OptionKey.B: "Przy piecu",
            },
            correct_option=OptionKey.A,
            explanation="Materiały łatwopalne muszą być w strefie wyznaczonej przepisami PPOŻ.",
            category="Tutorial",
        )

        # Mark onboarding as done
        profile = self.repo.get_or_create_profile(user_id)
        profile.has_completed_onboarding = True
        self.repo.save_profile(profile)

        self._reset_quiz_state([tutorial_q], "🎓 Szkolenie Wstępne")
        st.rerun()

    def submit_answer(
        self, user_id: str, question: Question, selected_option: str
    ) -> None:
        is_correct = selected_option == question.correct_option

        # 1. Update DB
        self.repo.save_attempt(user_id, question.id, is_correct)

        # 2. Update Session
        if is_correct:
            st.session_state.score += 1
        else:
            st.session_state.quiz_errors.append(question.id)

        st.session_state.answers_history.append(is_correct)
        st.session_state.feedback_mode = True
        st.session_state.last_feedback = {
            "is_correct": is_correct,
            "selected": selected_option,
            "correct_option": question.correct_option,
        }

    def next_question(self) -> None:
        st.session_state.current_index += 1
        st.session_state.feedback_mode = False
        st.session_state.last_feedback = None

        # Check if quiz is finished
        if st.session_state.current_index >= len(st.session_state.quiz_questions):
            st.session_state.screen = "summary"

    def update_language(self, user_id: str, lang_code: str) -> None:
        profile = self.repo.get_or_create_profile(user_id)
        profile.preferred_language = Language(lang_code)
        self.repo.save_profile(profile)
        # No st.rerun() here; let the caller decide or let Streamlit auto-rerun
