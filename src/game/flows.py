# src/game/flows.py

from src.config import GameConfig
from src.game.core import GameContext, GameFlow, GameStep
from src.game.steps import QuestionLoopStep, SummaryStep, TextStep
from src.quiz.domain.models import OptionKey, Question
from src.shared.telemetry import Telemetry


class DailySprintFlow(GameFlow):
    """
    The 'Smart' Daily Sprint.
    """

    def build_steps(self, context: GameContext) -> list[GameStep]:
        telemetry = Telemetry("DailySprintFlow")
        context.data["score"] = 0
        context.data["errors"] = []

        # 1. Ensure profile exists
        _ = context.repo.get_or_create_profile(context.user_id)

        # Logic: If streak > 3 days, we might give them a "Bonus" or just standard.
        # For now, let's keep the standard limit.
        limit = GameConfig.SPRINT_QUESTIONS

        # 2. Fetch Smart Mix
        questions = context.repo.get_smart_mix(context.user_id, limit)

        telemetry.log_info(f"Smart Mix fetched: {len(questions)} questions")

        if not questions:
            # Keep this TextStep only for the "All Mastered" edge case
            return [
                TextStep(
                    "Gratulacje! 🏆",
                    "Opanowałeś cały materiał! Wróć później na powtórkę.",
                    "Menu",
                )
            ]

        context.data["total_questions"] = len(questions)

        # --- CHANGE: Removed TextStep (Intro) ---
        return [
            # --- FIX: Added flow_title ---
            QuestionLoopStep(questions, flow_title="🚀 Codzienny Sprint"),
            SummaryStep(),
        ]


class CategorySprintFlow(GameFlow):
    """
    Focused learning on a specific topic.
    """

    def __init__(self, category: str):
        self.category = category

    def build_steps(self, context: GameContext) -> list[GameStep]:
        telemetry = Telemetry("CategorySprintFlow")
        context.data["score"] = 0
        context.data["errors"] = []

        limit = GameConfig.SPRINT_QUESTIONS

        # Fetch by Category
        questions = context.repo.get_questions_by_category(
            self.category, context.user_id, limit
        )

        telemetry.log_info(
            f"Category '{self.category}' fetched: {len(questions)} questions"
        )

        if not questions:
            return [
                TextStep("Pusto", f"Brak pytań w kategorii: {self.category}", "Menu")
            ]

        context.data["total_questions"] = len(questions)

        # --- CHANGE: Removed TextStep (Intro) ---
        return [
            # --- FIX: Added flow_title ---
            QuestionLoopStep(questions, flow_title=f"📚 {self.category}"),
            SummaryStep(),
        ]


class OnboardingFlow(GameFlow):
    # I kept the text steps here because it is a Tutorial,
    # but you can remove them if you want it instant too.
    def build_steps(self, context: GameContext) -> list[GameStep]:
        tutorial_q = Question(
            id="TUT-01",
            text="To jest pytanie treningowe. Gdzie składować materiały łatwopalne?",
            options={
                OptionKey.A: "W strefie bezpiecznej (Zielona)",
                OptionKey.B: "Przy piecu",
            },
            correct_option=OptionKey.A,
            explanation=(
                "Materiały łatwopalne muszą być w strefie wyznaczonej przepisami PPOŻ."
            ),
            category="Tutorial",
        )

        profile = context.repo.get_or_create_profile(context.user_id)
        profile.has_completed_onboarding = True
        context.repo.save_profile(profile)

        context.data["total_questions"] = 1
        return [
            TextStep(
                "👋 Witaj w Magazynie!",
                "Jesteś nowym operatorem wózka. Przejdźmy szybkie szkolenie BHP.",
                "Dalej",
            ),
            # --- FIX: Added flow_title ---
            QuestionLoopStep([tutorial_q], flow_title="🎓 Szkolenie Wstępne"),
            TextStep(
                "Szkolenie Zakończone",
                "Jesteś gotowy do pracy!",
                "Rozpocznij Sprint 🚀",
            ),
        ]
