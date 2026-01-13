from enum import Enum, auto
import logging

logger = logging.getLogger(__name__)


class QuizState(Enum):
    IDLE = auto()  # App loaded, waiting for user to start
    LOADING = auto()  # Fetching questions
    QUESTION_ACTIVE = auto()  # Displaying a question, waiting for input
    FEEDBACK_VIEW = auto()  # Answer submitted, showing explanation
    SUMMARY = auto()  # Quiz finished
    EMPTY_STATE = auto()  # No questions available


class QuizAction(Enum):
    START = auto()
    LOAD_SUCCESS = auto()
    LOAD_EMPTY = auto()
    SUBMIT_ANSWER = auto()
    NEXT_QUESTION = auto()
    FINISH_QUIZ = auto()
    RESET = auto()


class QuizStateMachine:
    """
    Pure FSM Logic.
    Adheres to SRP: It only cares about State Transitions, not UI or DB.
    """

    def __init__(self, initial_state=QuizState.IDLE):
        self._state = initial_state

    @property
    def current_state(self) -> QuizState:
        return self._state

    def transition(self, action: QuizAction):
        """
        The Transition Table.
        Defines strictly what is allowed.
        """
        previous = self._state

        # Transition Logic
        match (self._state, action):
            # IDLE -> LOADING
            case (QuizState.IDLE, QuizAction.START):
                self._state = QuizState.LOADING

            # LOADING -> ACTIVE or EMPTY
            case (QuizState.LOADING, QuizAction.LOAD_SUCCESS):
                self._state = QuizState.QUESTION_ACTIVE
            case (QuizState.LOADING, QuizAction.LOAD_EMPTY):
                self._state = QuizState.EMPTY_STATE

            # ACTIVE -> FEEDBACK
            case (QuizState.QUESTION_ACTIVE, QuizAction.SUBMIT_ANSWER):
                self._state = QuizState.FEEDBACK_VIEW

            # FEEDBACK -> ACTIVE (Next) or SUMMARY (Finish)
            case (QuizState.FEEDBACK_VIEW, QuizAction.NEXT_QUESTION):
                self._state = QuizState.QUESTION_ACTIVE
            case (QuizState.FEEDBACK_VIEW, QuizAction.FINISH_QUIZ):
                self._state = QuizState.SUMMARY

            # RESET Logic
            case (_, QuizAction.RESET):
                self._state = QuizState.IDLE

            # Catch-all for invalid transitions
            case _:
                logger.error(f"⛔ INVALID TRANSITION: {self._state.name} + {action.name}")
                return

        logger.info(f"🔄 FSM: {previous.name} --[{action.name}]--> {self._state.name}")