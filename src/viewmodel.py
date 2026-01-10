import streamlit as st
import logging
from typing import Optional, List
from src.models import Question, OptionKey, UserProfile
from src.service import QuizService

logger = logging.getLogger(__name__)


class QuizViewModel:
    def __init__(self, service: QuizService):
        self.service = service

    def ensure_state_initialized(self):
        defaults = {
            'quiz_questions': [],
            'current_index': 0,
            'score': 0,
            'answer_submitted': False,
            'last_feedback': None,
            'quiz_complete': False,
            'user_profile': None
        }
        for key, val in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = val

    @property
    def questions(self) -> List[Question]:
        return st.session_state.get('quiz_questions', [])

    @property
    def current_question(self) -> Optional[Question]:
        qs = st.session_state.get('quiz_questions', [])
        idx = st.session_state.get('current_index', 0)
        if qs and 0 <= idx < len(qs):
            return qs[idx]
        return None

    @property
    def is_complete(self) -> bool:
        return st.session_state.get('quiz_complete', False)

    @property
    def user_profile(self) -> Optional[UserProfile]:
        return st.session_state.get('user_profile', None)

    def load_quiz(self, mode: str, user_id: str):
        logger.info(f"🎮 VM: Requesting quiz load. Mode='{mode}', User='{user_id}'")
        qs = self.service.get_quiz_questions(mode, user_id)
        profile = self.service.get_user_profile(user_id)

        if not qs:
            logger.warning("🎮 VM: Service returned 0 questions!")
        else:
            logger.info(f"🎮 VM: Received {len(qs)} questions. First ID: {qs[0].id}")

        logger.info(f"🎮 VM: Loaded Profile. Progress: {profile.daily_progress}")

        st.session_state.quiz_questions = qs
        st.session_state.user_profile = profile
        st.session_state.current_index = 0
        st.session_state.score = 0
        st.session_state.answer_submitted = False
        st.session_state.last_feedback = None
        st.session_state.quiz_complete = False

    def submit_answer(self, user_id: str, selected_key: OptionKey):
        q = self.current_question
        if not q:
            logger.error("🎮 VM: Attempted to submit answer but 'current_question' is None!")
            return

        logger.info(f"👉 ACTION: User submitted '{selected_key}'. Correct is '{q.correct_option}' (QID: {q.id})")

        is_correct = self.service.submit_answer(user_id, q, selected_key)

        if is_correct:
            st.session_state.score += 1
            feedback = {"type": "success", "msg": "✅ Dobrze!", "explanation": None}
            logger.debug("✅ VM: Answer validated as CORRECT.")
        else:
            feedback = {"type": "error", "msg": f"❌ Poprawna: {q.correct_option.value}.",
                        "explanation": q.explanation}
            logger.debug("❌ VM: Answer validated as INCORRECT.")

        st.session_state.last_feedback = feedback
        st.session_state.answer_submitted = True
        st.session_state.user_profile = self.service.get_user_profile(user_id)
        logger.info(f"📊 STATE: Score updated to {st.session_state.score}. Progress: {st.session_state.current_index + 1}/{len(st.session_state.quiz_questions)}")
        if st.session_state.current_index >= len(st.session_state.quiz_questions) - 1:
            st.session_state.quiz_complete = True

    def next_question(self):
        prev_idx = st.session_state.current_index
        st.session_state.current_index += 1
        logger.debug(f"⏩ NAV: Moving from index {prev_idx} to {st.session_state.current_index}")
        st.session_state.answer_submitted = False
        st.session_state.last_feedback = None
        logger.debug(f"⏩ NAV: Moving from index {prev_idx} to {st.session_state.current_index}")

    def reset_progress(self, user_id: str):
        self.service.repo.reset_user_progress(user_id)
        st.session_state.user_profile = self.service.get_user_profile(user_id)
        st.session_state.quiz_questions = []