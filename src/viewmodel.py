import streamlit as st
import logging
from typing import Optional, List
from src.models import Question, OptionKey, UserProfile, QuizSessionState, QuizFeedback
from src.service import QuizService
from src.fsm import QuizStateMachine, QuizState, QuizAction

logger = logging.getLogger(__name__)


class QuizViewModel:
    def __init__(self, service: QuizService):
        self.service = service
        saved_state = st.session_state.get('fsm_state', QuizState.IDLE)
        self.fsm = QuizStateMachine(initial_state=saved_state)

        if 'quiz_state' not in st.session_state:
            st.session_state.quiz_state = QuizSessionState()

    def _persist_state(self):
        st.session_state.fsm_state = self.fsm.current_state

    # --- 🛡️ FORENSIC STATE MUTATOR ---
    def _mutate_state(self, action: str, **payload):
        """
        Centralized state modification.
        Every change to the session state passes through here for logging.
        """
        state = self.session_state

        # 1. Log Intent
        logger.info(f"⚡ MUTATION REQUEST: {action} | Payload: {payload}")

        # 2. Apply Changes
        if action == "REGISTER_CORRECT":
            state.record_correct_answer()
            q_id = payload.get('q_id')
            # Logic: If in correction, remove from error list
            if state.internal_phase == "Correction" and q_id:
                state.resolve_error(q_id)
                logger.debug(f"   -> Resolved error for Q{q_id}. Remaining: {len(state.session_error_ids)}")

        elif action == "REGISTER_ERROR":
            q_id = payload.get('q_id')
            if q_id:
                state.record_error(q_id)
                logger.debug(f"   -> Recorded error for Q{q_id}. Total: {len(state.session_error_ids)}")

        elif action == "SET_PHASE":
            new_phase = payload.get('phase')
            state.set_phase(new_phase)
            logger.info(f"   -> Phase transition: {new_phase}")

        elif action == "RESET_SESSION":
            st.session_state.quiz_state = QuizSessionState()
            st.session_state.quiz_state.set_phase(payload.get('phase', 'Sprint'))

        elif action == "NEXT_INDEX":
            state.current_q_index += 1
            state.last_selected_option = None
            state.last_feedback = None

        elif action == "SET_FEEDBACK":
            state.last_feedback = payload.get('feedback')
            state.last_selected_option = payload.get('selected_option')

    # --- Properties ---
    @property
    def state(self) -> QuizState:
        return self.fsm.current_state

    @property
    def session_state(self) -> QuizSessionState:
        return st.session_state.quiz_state

    @property
    def questions(self) -> List[Question]:
        return st.session_state.get('quiz_questions', [])

    @property
    def current_question(self) -> Optional[Question]:
        qs = self.questions
        idx = self.session_state.current_q_index
        if qs and 0 <= idx < len(qs):
            return qs[idx]
        return None

    @property
    def user_profile(self) -> Optional[UserProfile]:
        return st.session_state.get('user_profile', None)

    @property
    def dashboard_config(self):
        mode = st.session_state.get('current_mode', "Daily Sprint")
        user_id = st.session_state.get('last_user_id', "Unknown")
        return self.service.get_dashboard_config(mode, self.session_state, user_id, len(self.questions))

    # --- Actions ---

    def start_quiz(self, mode: str, user_id: str):
        self.fsm.transition(QuizAction.START)
        logger.info(f"🎮 VM: Loading Quiz Mode='{mode}'")

        st.session_state.current_mode = mode

        qs = self.service.get_quiz_questions(mode, user_id)
        profile = self.service.get_user_profile(user_id)

        st.session_state.quiz_questions = qs
        st.session_state.user_profile = profile

        # USE MUTATOR
        self._mutate_state("RESET_SESSION", phase="Sprint")

        if qs:
            self.fsm.transition(QuizAction.LOAD_SUCCESS)
        else:
            self.fsm.transition(QuizAction.LOAD_EMPTY)

        self._persist_state()

    def submit_answer(self, user_id: str, selected_key: OptionKey):
        q = self.current_question
        if not q: return

        is_correct = self.service.submit_answer(user_id, q, selected_key)

        if is_correct:
            self._mutate_state("REGISTER_CORRECT", q_id=q.id)
            fb = QuizFeedback(type="success", message="✅ Dobrze!")
            self._mutate_state("SET_FEEDBACK", feedback=fb, selected_option=selected_key)
        else:
            self._mutate_state("REGISTER_ERROR", q_id=q.id)

            fb = QuizFeedback(
                type="error",
                message=f"❌ Źle. Poprawna: {q.correct_option.value}.",
                explanation=q.explanation
            )
            self._mutate_state("SET_FEEDBACK", feedback=fb, selected_option=selected_key)

        st.session_state.user_profile = self.service.get_user_profile(user_id)
        self.fsm.transition(QuizAction.SUBMIT_ANSWER)
        self._persist_state()

    def next_step(self):
        mode = st.session_state.get('current_mode', "Daily Sprint")

        is_list_complete = self.service.is_quiz_complete(
            mode,
            self.session_state,
            len(self.questions)
        )

        if is_list_complete:
            if self.session_state.session_error_ids:
                logger.info(
                    f"🔄 VM: Errors detected ({len(self.session_state.session_error_ids)}). Looping Correction Phase.")
                self._transition_to_correction_phase()
            else:
                user_id = st.session_state.get('last_user_id', "Unknown")
                self.service.finalize_session(user_id)
                self.session_state.is_complete = True
                self.fsm.transition(QuizAction.FINISH_QUIZ)
        else:
            self._mutate_state("NEXT_INDEX")
            self.fsm.transition(QuizAction.NEXT_QUESTION)

        self._persist_state()

    def _transition_to_correction_phase(self):
        logger.info("🔄 VM: Switching to Correction Phase")

        error_ids = self.session_state.session_error_ids
        review_questions = self.service.repo.get_questions_by_ids(error_ids)

        st.session_state.quiz_questions = review_questions

        # Manual reset of index/score for new phase
        self.session_state.current_q_index = 0
        self.session_state.score = 0
        self.session_state.last_selected_option = None
        self.session_state.last_feedback = None

        if self.session_state.internal_phase != "Correction":
            st.toast(f"🚨 Czas na poprawę! Masz {len(review_questions)} błędów do naprawienia.", icon="🛠️")

        self._mutate_state("SET_PHASE", phase="Correction")

        self.fsm.transition(QuizAction.NEXT_QUESTION)

    def reset_quiz(self, user_id: str = None):
        if user_id:
            self.service.repo.reset_user_progress(user_id)

        st.session_state.quiz_questions = []
        self._mutate_state("RESET_SESSION")

        self.fsm.transition(QuizAction.RESET)
        self._persist_state()

    def ensure_state_initialized(self):
        if 'quiz_questions' not in st.session_state:
            st.session_state.quiz_questions = []
        if 'user_profile' not in st.session_state:
            st.session_state.user_profile = None