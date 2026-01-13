from typing import Optional, List
from src.quiz.domain.models import Question, OptionKey, UserProfile, QuizSessionState
from src.quiz.application.service import QuizService
from src.quiz.presentation.state_provider import IStateProvider
from src.shared.telemetry import Telemetry
from src.fsm import QuizStateMachine, QuizState, QuizAction


class QuizViewModel:
    def __init__(self, service: QuizService, state_provider: IStateProvider):
        self.service = service
        self.state = state_provider
        self.telemetry = Telemetry("ViewModel")

        # Initialize FSM
        saved_fsm = self.state.get('fsm_state', QuizState.IDLE)
        self.fsm = QuizStateMachine(initial_state=saved_fsm)

        # Initialize Session State if missing
        if self.state.get('quiz_session') is None:
            self.state.set('quiz_session', QuizSessionState())

    # --- Properties ---
    @property
    def current_state(self) -> QuizState:
        return self.fsm.current_state

    @property
    def session(self) -> QuizSessionState:
        return self.state.get('quiz_session')

    @property
    def questions(self) -> List[Question]:
        return self.state.get('questions', [])

    @property
    def current_question(self) -> Optional[Question]:
        qs = self.questions
        idx = self.session.current_q_index
        if qs and 0 <= idx < len(qs):
            return qs[idx]
        return None

    def get_dashboard_config(self):
        mode = self.state.get('current_mode', "Daily Sprint")
        user_id = self.state.get('user_id', "Unknown")
        return self.service.get_dashboard_config(mode, self.session, user_id, len(self.questions))

    # --- Actions (Traced) ---

    def start_quiz(self, mode: str, user_id: str):
        # 1. Start Trace
        trace_id = Telemetry.start_trace()
        self.telemetry.log_info("Action: Start Quiz", mode=mode, user_id=user_id)

        # 2. Logic
        self.fsm.transition(QuizAction.START)
        self.state.set('current_mode', mode)
        self.state.set('user_id', user_id)

        questions = self.service.get_quiz_questions(mode, user_id)
        self.state.set('questions', questions)

        # Reset Session
        new_session = QuizSessionState()
        self.state.set('quiz_session', new_session)

        if questions:
            self.fsm.transition(QuizAction.LOAD_SUCCESS)
        else:
            self.fsm.transition(QuizAction.LOAD_EMPTY)

        self._persist_fsm()

    def submit_answer(self, selected_key: OptionKey):
        trace_id = Telemetry.start_trace()
        user_id = self.state.get('user_id')
        q = self.current_question

        if not q:
            self.telemetry.log_error("Submit failed", Exception("No active question"))
            return

        is_correct = self.service.submit_answer(user_id, q, selected_key)

        # Update Session State
        if is_correct:
            self.session.record_correct_answer()
            if self.session.internal_phase == "Correction":
                self.session.resolve_error(q.id)
        else:
            self.session.record_error(q.id)

        self.state.set('last_selected', selected_key)
        self.state.set('last_correct', is_correct)

        self.fsm.transition(QuizAction.SUBMIT_ANSWER)
        self._persist_fsm()

    def next_step(self):
        Telemetry.start_trace()
        mode = self.state.get('current_mode')

        is_complete = self.service.is_quiz_complete(mode, self.session, len(self.questions))

        if is_complete:
            if self.session.session_error_ids:
                self._enter_correction_phase()
            else:
                self._finish_quiz()
        else:
            self.session.next_question()
            self.state.set('last_selected', None)  # Clear selection
            self.fsm.transition(QuizAction.NEXT_QUESTION)

        self._persist_fsm()

    def _enter_correction_phase(self):
        self.telemetry.log_info("Entering Correction Phase")
        error_ids = self.session.session_error_ids

        # Fetch specific questions for review
        review_qs = self.service.repository.get_questions_by_ids(error_ids)
        self.state.set('questions', review_qs)

        # Reset Index for new list
        self.session.reset(phase="Correction")

        self.fsm.transition(QuizAction.NEXT_QUESTION)

    def _finish_quiz(self):
        user_id = self.state.get('user_id')
        self.service.finalize_session(user_id)
        self.fsm.transition(QuizAction.FINISH_QUIZ)

    def reset(self):
        Telemetry.start_trace()
        self.fsm.transition(QuizAction.RESET)
        self._persist_fsm()

    def _persist_fsm(self):
        self.state.set('fsm_state', self.fsm.current_state)