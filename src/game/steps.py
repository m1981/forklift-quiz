from typing import List, Any, Union, Dict
from dataclasses import dataclass

from src.game.core import GameStep, GameContext, UIModel
from src.quiz.domain.models import Question, OptionKey


# --- 1. Text Step (For Onboarding / Story) ---

@dataclass
class TextStepPayload:
    title: str
    content: str
    button_text: str
    image_path: str = None


class TextStep(GameStep):
    """
    Displays a static screen with text and a 'Next' button.
    Useful for: Onboarding, Story segments, Level transitions.
    """

    def __init__(self, title: str, content: str, button_text: str = "Dalej", image_path: str = None):
        self.payload = TextStepPayload(title, content, button_text, image_path)

    def enter(self, context: GameContext):
        pass  # No special initialization needed

    def get_ui_model(self) -> UIModel:
        return UIModel(type="TEXT", payload=self.payload)

    def handle_action(self, action: str, payload: Any, context: GameContext) -> Union['GameStep', str, None]:
        if action == "NEXT":
            return "NEXT"
        return None


# --- 2. Question Loop Step (The Core Gameplay) ---

@dataclass
class QuestionStepPayload:
    question: Question
    current_index: int
    total_count: int
    last_feedback: Dict = None  # { 'is_correct': bool, 'correct_option': ... }


class QuestionLoopStep(GameStep):
    """
    Manages a list of questions.
    Handles: Display -> Submit -> Feedback -> Next.
    """

    def __init__(self, questions: List[Question]):
        self.questions = questions
        self.index = 0
        self.feedback_mode = False
        self.last_result = None

    def enter(self, context: GameContext):
        # Initialize score in the shared context if not present
        if 'score' not in context.data:
            context.data['score'] = 0
        if 'errors' not in context.data:
            context.data['errors'] = []

    def get_ui_model(self) -> UIModel:
        current_q = self.questions[self.index]

        payload = QuestionStepPayload(
            question=current_q,
            current_index=self.index + 1,
            total_count=len(self.questions),
            last_feedback=self.last_result if self.feedback_mode else None
        )

        # We use different UI types to tell the View how to render
        ui_type = "FEEDBACK" if self.feedback_mode else "QUESTION"
        return UIModel(type=ui_type, payload=payload)

    def handle_action(self, action: str, payload: Any, context: GameContext) -> Union['GameStep', str, None]:
        current_q = self.questions[self.index]

        if action == "SUBMIT_ANSWER":
            selected_option = payload  # e.g., OptionKey.A
            is_correct = (selected_option == current_q.correct_option)

            # 1. Update Context (Score/Errors)
            if is_correct:
                context.data['score'] += 1
            else:
                context.data['errors'].append(current_q.id)

            # 2. Persist to DB (Side Effect)
            # Note: In a pure engine, we might delegate this, but calling repo here is pragmatic.
            context.repo.save_attempt(context.user_id, current_q.id, is_correct)

            # 3. Set Feedback State
            self.feedback_mode = True
            self.last_result = {
                'is_correct': is_correct,
                'selected': selected_option,
                'correct_option': current_q.correct_option,
                'explanation': current_q.explanation
            }
            return None  # Stay on this step to show feedback

        elif action == "NEXT_QUESTION":
            # Advance index
            self.index += 1
            self.feedback_mode = False
            self.last_result = None

            # Check if loop is finished
            if self.index >= len(self.questions):
                return "NEXT"  # Exit this step

            return None  # Stay on this step (show next question)

        return None


# --- 3. Summary Step (Results) ---

@dataclass
class SummaryPayload:
    score: int
    total: int
    message: str

class SummaryStep(GameStep):
    def enter(self, context: GameContext):
        super().enter(context) # Ensure context is stored

    def get_ui_model(self) -> UIModel:
        # Read data from the Blackboard (Context)
        score = self.context.data.get('score', 0)

        # We need to know total questions.
        # Ideally, QuestionLoopStep should write this to context, or we pass it in constructor.
        # For now, let's assume we track it in context.data['total_questions']
        total = self.context.data.get('total_questions', 0)

        return UIModel(type="SUMMARY", payload=SummaryPayload(
            score=score,
            total=total,
            message="Quiz Finished"
        ))

    def handle_action(self, action: str, payload: Any, context: GameContext) -> Union['GameStep', str, None]:
        if action == "FINISH":
            return "NEXT"
        return None