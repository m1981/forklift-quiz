import json
import os

from src.quiz.domain.models import Question
from src.quiz.domain.ports import IQuizRepository
from src.shared.telemetry import Telemetry

# --- ADR 004: Seeding Strategy ---
# Decision: The Seeder relies on the Repository to check for emptiness.
# Rationale: While IQuizRepository does not strictly enforce an `is_empty()`
# method in the interface (Port), we use duck-typing here to allow the SQLite
# implementation to provide this optimization. In a stricter Hexagonal
# implementation, we would add `count()` to the Port, but for this MVP,
# checking the attribute existence is sufficient.
# ---------------------------------


class DataSeeder:
    """
    Responsible for populating the database with initial data.
    """

    def __init__(self, repo: IQuizRepository) -> None:
        self.repo = repo
        self.telemetry = Telemetry("DataSeeder")

    def seed_if_empty(self, seed_file: str = "data/seed_questions_demo.json") -> None:
        """
        Checks if the repository is empty, and if so, loads data from JSON.
        """
        try:
            # Check if repo supports emptiness check (See ADR 004)
            if hasattr(self.repo, "is_empty") and not self.repo.is_empty():
                return

            self.telemetry.log_info("DB appears empty. Attempting to seed...")

            if os.path.exists(seed_file):
                with open(seed_file, encoding="utf-8") as f:
                    data = json.load(f)
                    questions = [Question(**q) for q in data]
                    self.repo.seed_questions(questions)
                    self.telemetry.log_info(f"Seeded {len(questions)} questions.")
            else:
                self.telemetry.log_error(
                    "Seed file NOT found", Exception(f"Missing: {seed_file}")
                )
        except Exception as e:
            self.telemetry.log_error("Auto-seeding failed", e)
