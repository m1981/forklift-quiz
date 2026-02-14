import random

from src.quiz.domain.models import Question


class CategorySelector:
    """
    Pure domain logic for Category Mode question selection.
    Ensures consistent behavior across all repository implementations.
    """

    @staticmethod
    def prioritize_weak_questions(
        questions_with_streaks: list[tuple[Question, int]], limit: int
    ) -> list[Question]:
        """
        Sort questions by mastery level (weakest first), randomize ties.

        Args:
            questions_with_streaks: List of (Question, consecutive_correct) tuples
            limit: Maximum number of questions to return

        Returns:
            Sorted and limited list of Questions

        Example:
            >>> questions = [(q1, 5), (q2, 0), (q3, 2)]
            >>> result = CategorySelector.prioritize_weak_questions(questions, 2)
            >>> # Returns [q2, q3] (weakest first)
        """
        if not questions_with_streaks:
            return []

        # Sort by streak (ascending), then random for ties
        sorted_candidates = sorted(
            questions_with_streaks, key=lambda x: (x[1], random.random())
        )

        return [q for q, _ in sorted_candidates[:limit]]
