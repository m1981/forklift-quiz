import random

from src.config import GameConfig
from src.quiz.domain.models import Question, QuestionCandidate
from src.shared.telemetry import Telemetry


class SpacedRepetitionSelector:
    """
    Pure Domain Logic.
    Encapsulates the rules for generating a 'Smart Mix' of questions.
    """

    def __init__(self) -> None:
        self.telemetry = Telemetry("SpacedRepetitionSelector")

    def select(self, candidates: list[QuestionCandidate], limit: int) -> list[Question]:
        # 1. Segregate Pools
        new_pool = [c for c in candidates if not c.is_seen]
        learning_pool = [
            c
            for c in candidates
            if c.is_seen and c.streak < GameConfig.MASTERY_THRESHOLD
        ]
        review_pool = [
            c
            for c in candidates
            if c.is_seen and c.streak >= GameConfig.MASTERY_THRESHOLD
        ]

        self.telemetry.log_info(
            "Spaced Repetition Pools",
            new=len(new_pool),
            learning=len(learning_pool),
            review=len(review_pool),
        )

        # 2. Calculate Targets
        target_new = int(limit * GameConfig.NEW_RATIO)
        target_review = limit - target_new

        selected_dtos: list[QuestionCandidate] = []

        # 3. Selection Logic
        random.shuffle(new_pool)
        random.shuffle(learning_pool)
        random.shuffle(review_pool)

        # Prioritize Learning + Review
        mixed_review = learning_pool + review_pool
        selected_dtos.extend(mixed_review[:target_review])

        # Fill with New
        selected_dtos.extend(new_pool[:target_new])

        # Backfill strategies
        if len(selected_dtos) < limit:
            needed = limit - len(selected_dtos)
            selected_dtos.extend(mixed_review[target_review:][:needed])

        if len(selected_dtos) < limit:
            needed = limit - len(selected_dtos)
            selected_dtos.extend(new_pool[target_new:][:needed])

        random.shuffle(selected_dtos)

        return [c.question for c in selected_dtos]
