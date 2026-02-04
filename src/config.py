import os
from enum import Enum
from typing import Final


class Category(Enum):
    # Enum Member = ("Category Name", "Icon")
    BHP = ("Bezpieczeństwo i Organizacja Pracy", "🦺")
    DIAGRAMS = ("Diagramy Udźwigu i Ładunki", "📦")
    LAW = ("Prawo i Dozór Techniczny", "📜")
    CONSTRUCTION = ("Budowa i Parametry Techniczne", "⚙️")
    POWER = ("Napęd i Zasilanie", "🔋")
    EQUIPMENT = ("Wyposażenie i Kontrolki", "🕹️")

    def __init__(self, label: str, icon: str):
        self.label = label
        self.icon = icon

    @classmethod
    def get_icon(cls, label: str) -> str:
        """Returns the icon for a given category label, or a default."""
        for category in cls:
            if category.label == label:
                return category.icon
        return "🔨"  # Default fallback

    @classmethod
    def all_labels(cls) -> list[str]:
        """Returns a list of all category names (for the game logic)."""
        return [c.label for c in cls]


class GameConfig:
    # --- Infrastructure Switch ---
    USE_SQLITE: bool = True  # Changed from "true" string to boolean

    # --- App Identity ---
    APP_TITLE = "Wózki widłowe 2 WJO"
    # Path to your logo file (relative to project root)
    # Ensure this file exists, or the code will fallback to a placeholder
    APP_LOGO_PATH = "assets/logo.jpg"

    DEMO_QUESTION_IDS: Final[list[str]] = ["1", "2", "3", "4", "5"]

    # --- Game Rules ---
    DAILY_GOAL = 3
    SPRINT_QUESTIONS: Final[int] = 15
    PASSING_SCORE = 11

    # --- Mastery Algorithm ---
    MASTERY_THRESHOLD = 1
    NEW_RATIO = 0.6

    # --- Categories ---
    # Now we just reference the Enum, ensuring consistency
    CATEGORIES = Category.all_labels()

    @staticmethod
    def get_demo_logo_path(prospect_slug: str | None) -> str:
        """Returns path to assets/logos/{slug}.png"""
        if not prospect_slug:
            return GameConfig.APP_LOGO_PATH

        safe_slug = "".join(c for c in prospect_slug if c.isalnum() or c in "_-")
        path = f"assets/logos/{safe_slug}.png"

        if not os.path.exists(path):
            return GameConfig.APP_LOGO_PATH
        return path
