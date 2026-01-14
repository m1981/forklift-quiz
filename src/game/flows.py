from typing import List
from src.game.core import GameFlow, GameStep, GameContext
from src.game.steps import TextStep, QuestionLoopStep, SummaryStep
from src.quiz.domain.models import Question, OptionKey


# --- 1. The Daily Sprint Scenario ---

class DailySprintFlow(GameFlow):
    """
    The standard daily workflow:
    1. Fetch questions based on logic (Sprint vs Bonus).
    2. Run the Question Loop.
    3. Show Summary.
    """

    def build_steps(self, context: GameContext) -> List[GameStep]:
        # 1. Fetch User Profile to determine mode
        profile = context.repo.get_or_create_profile(context.user_id)

        # 2. Determine Logic (Bonus vs Standard)
        # Note: We are migrating logic from the old 'Strategies' here.
        # In a pure refactor, we might inject a 'QuestionProvider' service,
        # but for now, we'll keep the logic explicit to show the flow.

        is_bonus = profile.daily_progress >= profile.daily_goal

        if is_bonus:
            intro_title = "🔥 Runda Bonusowa"
            intro_msg = "Już wykonałeś cel dzienny! To są nadgodziny dla ambitnych."
            limit = 5
        else:
            intro_title = "🚀 Codzienny Sprint"
            intro_msg = f"Cel na dziś: {profile.daily_progress}/{profile.daily_goal}. Zaczynamy?"
            limit = 10

        # 3. Fetch Questions (Using Repo)
        # We reuse the repo logic. Ideally, repo methods should be granular.
        # For this implementation, let's assume we fetch all and filter,
        # or use the existing strategy logic if we kept it.
        # Let's simulate a clean fetch for the engine:
        all_qs = context.repo.get_all_questions()
        # (Simplified selection logic for brevity - in prod, use the Strategy class here)
        questions = all_qs[:limit]

        if not questions:
            return [
                TextStep("Brak Pytań", "Wróć jutro!", "Menu")
            ]

        # Pre-calculation for SummaryStep
        context.data['total_questions'] = len(questions)

        return [
            TextStep(intro_title, intro_msg, "Start"),
            QuestionLoopStep(questions),
            SummaryStep()
        ]


# --- 2. The Onboarding Scenario (New Requirement) ---

class OnboardingFlow(GameFlow):
    """
    A fixed tutorial flow for new users.
    Intro -> 1 Fixed Question -> Outro.
    """

    def build_steps(self, context: GameContext) -> List[GameStep]:
        # Hardcoded tutorial question
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

        context.data['total_questions'] = 1
        return [
            TextStep(
                title="👋 Witaj w Magazynie!",
                content="Jesteś nowym operatorem wózka. Przejdźmy szybkie szkolenie BHP.",
                button_text="Dalej"
            ),
            TextStep(
                title="Zasady Gry",
                content="Codziennie otrzymasz 10 pytań. Buduj serię (Streak) logując się codziennie.",
                button_text="Rozumiem"
            ),
            QuestionLoopStep([tutorial_q]),
            TextStep(
                title="Szkolenie Zakończone",
                content="Jesteś gotowy do pracy! Kliknij poniżej, aby przejść do menu głównego.",
                button_text="Zakończ"
            )
        ]