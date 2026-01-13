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

    def ensure_state_initialized(self):
        if 'quiz_questions' not in st.session_state:
            st.session_state.quiz_questions = []
        if 'user_profile' not in st.session_state:
            st.session_state.user_profile = None

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

        return self.service.get_dashboard_config(
            mode,
            self.session_state,
            user_id,
            len(self.questions)
        )

    # --- Actions ---

    def start_quiz(self, mode: str, user_id: str):
        self.fsm.transition(QuizAction.START)
        logger.info(f"🎮 VM: Loading Quiz Mode='{mode}'")

        st.session_state.current_mode = mode

        qs = self.service.get_quiz_questions(mode, user_id)
        profile = self.service.get_user_profile(user_id)

        st.session_state.quiz_questions = qs
        st.session_state.user_profile = profile

        # Reset State & Session Errors
        st.session_state.quiz_state = QuizSessionState()
        st.session_state.quiz_state.internal_phase = "Sprint"  # Default start

        if qs:
            self.fsm.transition(QuizAction.LOAD_SUCCESS)
        else:
            self.fsm.transition(QuizAction.LOAD_EMPTY)

        self._persist_state()

    def submit_answer(self, user_id: str, selected_key: OptionKey):
        q = self.current_question
        if not q: return

        is_correct = self.service.submit_answer(user_id, q, selected_key)

        self.session_state.last_selected_option = selected_key

        if is_correct:
            self.session_state.score += 1
            self.session_state.last_feedback = QuizFeedback(type="success", message="✅ Dobrze!")
        else:
            # TRACK ERROR FOR IMMEDIATE REVIEW
            if q.id not in self.session_state.session_error_ids:
                self.session_state.session_error_ids.append(q.id)
                logger.info(
                    f"📝 VM: Added Q{q.id} to session error list. Total errors: {len(self.session_state.session_error_ids)}")

            self.session_state.last_feedback = QuizFeedback(
                type="error",
                message=f"❌ Źle. Poprawna: {q.correct_option.value}.",
                explanation=q.explanation
            )

        st.session_state.user_profile = self.service.get_user_profile(user_id)
        self.fsm.transition(QuizAction.SUBMIT_ANSWER)
        self._persist_state()

    def next_step(self):
        mode = st.session_state.get('current_mode', "Daily Sprint")

        # 1. Check if current list of questions is done
        is_list_complete = self.service.is_quiz_complete(
            mode,
            self.session_state,
            len(self.questions)
        )

        if is_list_complete:
            # 2. ROUTING LOGIC (The "Daily Loop")

            # If we are in Sprint Mode and have errors -> Force Correction
            if self.session_state.internal_phase == "Sprint" and self.session_state.session_error_ids:
                self._transition_to_correction_phase()

            else:
                # Victory! (Either Sprint was perfect, or Correction is done)
                user_id = st.session_state.get('last_user_id', "Unknown")
                self.service.finalize_session(user_id)
                self.session_state.is_complete = True
                self.fsm.transition(QuizAction.FINISH_QUIZ)
        else:
            self.session_state.current_q_index += 1
            self.session_state.last_selected_option = None
            self.session_state.last_feedback = None
            self.fsm.transition(QuizAction.NEXT_QUESTION)

        self._persist_state()

    def _transition_to_correction_phase(self):
        """
        Swaps the question set to the ones missed.
        """
        logger.info("🔄 VM: Switching to Correction Phase")

        error_ids = self.session_state.session_error_ids
        review_questions = self.service.repo.get_questions_by_ids(error_ids)

        # Update State
        st.session_state.quiz_questions = review_questions
        self.session_state.current_q_index = 0
        self.session_state.score = 0
        self.session_state.internal_phase = "Correction"
        self.session_state.last_selected_option = None
        self.session_state.last_feedback = None

        st.toast(f"🚨 Czas na poprawę! Masz {len(review_questions)} błędów do naprawienia.", icon="🛠️")

        self.fsm.transition(QuizAction.NEXT_QUESTION)