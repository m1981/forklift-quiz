from typing import List
from src.game.core import GameFlow, GameStep, GameContext
from src.game.steps import TextStep, QuestionLoopStep, SummaryStep
from src.quiz.domain.models import Question, OptionKey
from src.config import GameConfig
from src.shared.telemetry import Telemetry # <--- NEW IMPORT

class DailySprintFlow(GameFlow):
    """
    The standard daily workflow:
    1. Fetch questions based on logic (Sprint vs Bonus).
    2. Run the Question Loop.
    3. Show Summary.
    """

    def build_steps(self, context: GameContext) -> List[GameStep]:
        telemetry = Telemetry("DailySprintFlow") # <--- INIT TELEMETRY

        context.data['score'] = 0
        context.data['errors'] = []

        # 1. Fetch User Profile to determine mode
        profile = context.repo.get_or_create_profile(context.user_id)
        is_bonus = profile.daily_progress >= profile.daily_goal

        if is_bonus:
            intro_title = "🔥 Runda Bonusowa"
            intro_msg = "Już wykonałeś cel dzienny! To są nadgodziny dla ambitnych."
            limit = GameConfig.BONUS_QUESTIONS
        else:
            intro_title = "🚀 Codzienny Sprint"
            intro_msg = f"Cel na dziś: {profile.daily_progress}/{profile.daily_goal}. Zaczynamy?"
            limit = GameConfig.SPRINT_QUESTIONS


        # 3. Fetch Questions (Using Repo)
        # We reuse the repo logic. Ideally, repo methods should be granular.
        # For this implementation, let's assume we fetch all and filter,
        # or use the existing strategy logic if we kept it.
        # Let's simulate a clean fetch for the engine:
        all_qs = context.repo.get_all_questions()

        # <--- LOGGING THE CRITICAL DATA POINT
        telemetry.log_info(f"Questions available in DB: {len(all_qs)}")

        questions = all_qs[:limit]

        if not questions:
            telemetry.log_error("No questions found!", Exception("DB returned 0 questions"))
            return [TextStep("Brak Pytań", "Wróć jutro!", "Menu")]

        context.data['total_questions'] = len(questions)

        return [
            TextStep(intro_title, intro_msg, "Start"),
            QuestionLoopStep(questions),
            SummaryStep()
        ]

class OnboardingFlow(GameFlow):
    def build_steps(self, context: GameContext) -> List[GameStep]:
        tutorial_q = Question(
            id="TUT-01",
            text="To jest pytanie treningowe. Gdzie składować materiały łatwopalne?",
            options={
                OptionKey.A: "W strefie bezpiecznej (Zielona)",
                OptionKey.B: "Przy piecu"
            },
            correct_option=OptionKey.A,
            explanation="Materiały łatwopalne muszą być w strefie wyznaczonej przepisami PPOŻ.",
            category="Tutorial"
        )

        # Mark as onboarded
        profile = context.repo.get_or_create_profile(context.user_id)
        profile.has_completed_onboarding = True
        context.repo.save_profile(profile)

        context.data['total_questions'] = 1
        return [
            TextStep("👋 Witaj w Magazynie!", "Jesteś nowym operatorem wózka. Przejdźmy szybkie szkolenie BHP.", "Dalej"),
            TextStep("Zasady Gry", "Codziennie otrzymasz 15 pytań. Buduj serię (Streak) logując się codziennie.", "Rozumiem"),
            QuestionLoopStep([tutorial_q]),
            TextStep("Szkolenie Zakończone", "Jesteś gotowy do pracy! Kliknij poniżej, aby rozpocząć pierwszy sprint.", "Rozpocznij Sprint 🚀")
        ]