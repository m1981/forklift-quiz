import base64
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

    @staticmethod
    def get_image_base64(path: str) -> str:
        """
        Converts a local image path to a Base64 Data URI for HTML embedding.
        Handles both local paths and web URLs.
        """
        # Debug Log 1: What are we trying to load?
        print(f"DEBUG: get_image_base64 called with path: '{path}'")

        # 1. Pass through web URLs
        if path.startswith("http"):
            print("DEBUG: Path is a URL. Passing through.")
            return path

        # 2. Convert local file
        # Debug Log 2: Check absolute path to verify CWD (Current Working Directory)
        abs_path = os.path.abspath(path)
        print(f"DEBUG: Absolute path resolved to: '{abs_path}'")

        if os.path.exists(path):
            try:
                print("DEBUG: File exists. Attempting to read...")
                with open(path, "rb") as img_file:
                    b64_data = base64.b64encode(img_file.read()).decode("utf-8")

                    # Determine mime type
                    mime = "image/png"
                    lower_path = path.lower()
                    if lower_path.endswith(".jpg") or lower_path.endswith(".jpeg"):
                        mime = "image/jpeg"
                    elif lower_path.endswith(".svg"):
                        mime = "image/svg+xml"

                    print(
                        f"DEBUG: Success! Generated Base64 string (len={len(b64_data)})"
                    )
                    return f"data:{mime};base64,{b64_data}"
            except Exception as e:
                print(f"DEBUG: Error reading file: {e}")
                pass  # Fallback below
        else:
            print("DEBUG: File NOT found at path.")

        # 3. Fallback (Transparent pixel)
        print("DEBUG: Returning Fallback 1x1 Pixel.")
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
