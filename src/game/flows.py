# src/game/flows.py

from src.config import GameConfig
from src.game.core import GameContext, GameFlow, GameStep
from src.game.steps import QuestionLoopStep, SummaryStep, TextStep
from src.quiz.domain.models import OptionKey, Question
from src.quiz.domain.spaced_repetition import SpacedRepetitionSelector
from src.shared.telemetry import Telemetry


class DailySprintFlow(GameFlow):
    """
    Use Case: Start Daily Sprint
    """

    def build_steps(self, context: GameContext) -> list[GameStep]:
        telemetry = Telemetry("DailySprintFlow")
        context.data["score"] = 0
        context.data["errors"] = []

        # 1. Infrastructure: Ensure profile
        _ = context.repo.get_or_create_profile(context.user_id)

        # 2. Infrastructure: Fetch Raw Data
        candidates = context.repo.get_repetition_candidates(context.user_id)

        # 3. Domain Logic: Apply Spaced Repetition Rules
        selector = SpacedRepetitionSelector()
        questions = selector.select(candidates, limit=GameConfig.SPRINT_QUESTIONS)

        telemetry.log_info(f"Daily Sprint Generated: {len(questions)} questions")

        if not questions:
            # Keep this TextStep only for the "All Mastered" edge case
            return [
                TextStep(
                    title="Gratulacje! 🏆",
                    content="Opanowałeś cały materiał! Wróć później na powtórkę.",
                    button_text="Menu",
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
                TextStep(
                    title="Pusto",
                    content=f"Brak pytań w kategorii: {self.category}",
                    button_text="Menu",
                )
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
                title="👋 Witaj w Magazynie!",
                content="Jesteś nowym operatorem wózka. Przejdźmy szybkie szkolenie BHP.",
                button_text="Dalej",
            ),
            # --- FIX: Added flow_title ---
            QuestionLoopStep([tutorial_q], flow_title="🎓 Szkolenie Wstępne"),
            TextStep(
                title="Szkolenie Zakończone",
                content="Jesteś gotowy do pracy!",
                button_text="Rozpocznij Sprint 🚀",
            ),
        ]


class DemoFlow(GameFlow):
    """
    Special flow for sales demos.
    - Fixed set of questions.
    - No spaced repetition algorithm.
    """

    def build_steps(self, context: GameContext) -> list[GameStep]:
        # 1. Fetch specific questions defined in Config
        target_ids = GameConfig.DEMO_QUESTION_IDS
        questions = context.repo.get_questions_by_ids(target_ids)

        # Fallback if IDs are wrong/missing in DB
        if not questions:
            return [
                TextStep(
                    title="Konfiguracja Demo",
                    content="Nie znaleziono pytań demo w bazie danych.",
                    button_text="Zamknij",
                )
            ]

        context.data["total_questions"] = len(questions)
        context.data["score"] = 0
        context.data["errors"] = []

        # --- RICH MARKDOWN CONTENT ---
        # We use standard Markdown.
        # <br> is used for line breaks within a bullet point.
        # ### is used for the main headline.

        demo_intro_md = """
### 🚀 **Zdasz za pierwszym razem.**
Inteligentna nauka do egzaminu UDT.

💡 **Inteligentne Wyjaśnienia**
Zrozum sens, a nie tylko wkuwaj.

⚠️ **Unikaj Pułapek Egzaminacyjnych**
Ostrzeżenia przed podchwytliwymi pytaniami.

🌍 **PL 🇵🇱 / UA 🇺🇦 / EN 🇬🇧**
Ucz się pytań w swoim języku, żeby zrozumieć. Zdawaj po polsku.


"""

        #  🛡 **Symulator Stresu**
        # Próbny egzamin identyczny jak w UDT.
        #
        # 📊 **Twoje Postępy**
        # Widzisz czarno na białym, kiedy jesteś gotowy, by zdać.
        #
        # 🧠 **Inteligentny Mix**
        # Algorytm uczy Cię tylko tego, czego nie umiesz. Oszczędź 50% czasu.

        return [
            TextStep(
                title="",  # Empty title so Markdown header takes over
                content=demo_intro_md,  # Correct argument name
                button_text="Rozpocznij Test 🚀",  # Correct argument name
            ),
            QuestionLoopStep(questions, flow_title="⭐ Demo"),
            SummaryStep(),
        ]
