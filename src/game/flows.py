from src.config import GameConfig
from src.game.core import GameContext, GameFlow, GameStep
from src.game.steps import QuestionLoopStep, SummaryStep, TextStep
from src.quiz.domain.models import OptionKey, Question
from src.shared.telemetry import Telemetry


class DailySprintFlow(GameFlow):
    """
    The 'Smart' Daily Sprint.
    Uses the Repository's 'Brain' to mix new and review questions.
    """

    def build_steps(self, context: GameContext) -> list[GameStep]:
        telemetry = Telemetry("DailySprintFlow")
        context.data["score"] = 0
        context.data["errors"] = []

        # 1. Check Bonus Mode (Streak based)
        # We call this to ensure profile exists, but we don't use the return value yet.
        _ = context.repo.get_or_create_profile(context.user_id)

        # Logic: If streak > 3 days, we might give them a "Bonus" or just standard.
        # For now, let's keep the standard limit.
        limit = GameConfig.SPRINT_QUESTIONS

        # 2. Fetch Smart Mix (The new Logic)
        questions = context.repo.get_smart_mix(context.user_id, limit)

        telemetry.log_info(f"Smart Mix fetched: {len(questions)} questions")

        if not questions:
            # This happens if the user has MASTERED 100% of the DB!
            return [
                TextStep(
                    "Gratulacje! 🏆",
                    "Opanowałeś cały materiał! Wróć później na powtórkę.",
                    "Menu",
                )
            ]

        context.data["total_questions"] = len(questions)

        return [
            TextStep(
                "Codzienny Sprint 🚀",
                f"Wybraliśmy dla Ciebie {len(questions)} pytań. Powodzenia!",
                "Start",
            ),
            QuestionLoopStep(questions),
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

        return [
            TextStep(
                f"Temat: {self.category}",
                "Skupiamy się na jednym temacie. Do dzieła!",
                "Start",
            ),
            QuestionLoopStep(questions),
            SummaryStep(),
        ]


class OnboardingFlow(GameFlow):
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

        # Mark as onboarded
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
            TextStep(
                "Zasady Gry",
                (
                    "Codziennie otrzymasz 15 pytań. "
                    "Buduj serię (Streak) logując się codziennie."
                ),
                "Rozumiem",
            ),
            QuestionLoopStep([tutorial_q]),
            TextStep(
                "Szkolenie Zakończone",
                (
                    "Jesteś gotowy do pracy! "
                    "Kliknij poniżej, aby rozpocząć pierwszy sprint."
                ),
                "Rozpocznij Sprint 🚀",
            ),
        ]
