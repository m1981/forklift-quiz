import streamlit as st
import logging
from typing import Optional, List
from src.models import Question, OptionKey, UserProfile
from src.service import QuizService
from src.fsm import QuizStateMachine, QuizState, QuizAction

logger = logging.getLogger(__name__)

class QuizViewModel:
    def __init__(self, service: QuizService):
        self.service = service
        # Restore FSM state from session or default to IDLE
        saved_state = st.session_state.get('fsm_state', QuizState.IDLE)
        self.fsm = QuizStateMachine(initial_state=saved_state)

    def _persist_state(self):
        """Save FSM state to Streamlit session so it survives reruns"""
        st.session_state.fsm_state = self.fsm.current_state

    def ensure_state_initialized(self):
        """Initialize data containers"""
        defaults = {
            'quiz_questions': [],
            'current_index': 0,
            'score': 0,
            'last_feedback': None,
            'user_profile': None,
            'last_selected_option': None,
            'fsm_state': QuizState.IDLE
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    # --- Properties ---
    @property
    def state(self) -> QuizState:
        return self.fsm.current_state

    @property
    def questions(self) -> List[Question]:
        return st.session_state.get('quiz_questions', [])

    @property
    def current_question(self) -> Optional[Question]:
        qs = self.questions
        idx = st.session_state.get('current_index', 0)
        if qs and 0 <= idx < len(qs):
            return qs[idx]
        return None

    @property
    def user_profile(self) -> Optional[UserProfile]:
        return st.session_state.get('user_profile', None)

    # --- Actions ---

    def start_quiz(self, mode: str, user_id: str):
        """Action: IDLE -> LOADING -> (ACTIVE or EMPTY)"""
        self.fsm.transition(QuizAction.START)

        logger.info(f"🎮 VM: Loading Quiz Mode='{mode}'")
        qs = self.service.get_quiz_questions(mode, user_id)
        profile = self.service.get_user_profile(user_id)

        # 2. Update Data State
        st.session_state.quiz_questions = qs
        st.session_state.user_profile = profile
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.last_feedback = None
        st.session_state.last_selected_option = None

        # 3. Trigger Resulting Transition
        if qs:
            self.fsm.transition(QuizAction.LOAD_SUCCESS)
        else:
            self.fsm.transition(QuizAction.LOAD_EMPTY)

        self._persist_state()

    def submit_answer(self, user_id: str, selected_key: OptionKey):
        """Action: ACTIVE -> FEEDBACK"""
        q = self.current_question
        if not q: return

        # 1. Side Effect: DB Update
        is_correct = self.service.submit_answer(user_id, q, selected_key)

        # 2. Update UI Data
        st.session_state.last_selected_option = selected_key
        if is_correct:
            st.session_state.score += 1
            st.session_state.last_feedback = {"type": "success", "msg": "✅ Dobrze!"}
        else:
            st.session_state.last_feedback = {
                "type": "error",
                "msg": f"❌ Źle. Poprawna: {q.correct_option.value}.",
                "explanation": q.explanation
            }

        # Refresh profile to show updated stats immediately
        st.session_state.user_profile = self.service.get_user_profile(user_id)

        # 3. Transition
        self.fsm.transition(QuizAction.SUBMIT_ANSWER)
        self._persist_state()

    def next_step(self):
        """Action: FEEDBACK -> (ACTIVE or SUMMARY)"""
        is_last_question = st.session_state.current_index >= len(self.questions) - 1

        if is_last_question:
            self.fsm.transition(QuizAction.FINISH_QUIZ)
        else:
            st.session_state.current_index += 1
            st.session_state.last_selected_option = None
            st.session_state.last_feedback = None
            self.fsm.transition(QuizAction.NEXT_QUESTION)

        self._persist_state()

    def reset_quiz(self, user_id: str = None):
        """Action: ANY -> IDLE"""
        if user_id:
            self.service.repo.reset_user_progress(user_id)

        # Clear Data
        st.session_state.quiz_questions = []
        st.session_state.current_index = 0

        self.fsm.transition(QuizAction.RESET)
        self._persist_state()