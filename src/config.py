# src/config.py


class GameConfig:
    # --- Game Rules ---
    DAILY_GOAL = 3  # Streaks
    SPRINT_QUESTIONS = 15  # Questions per round
    PASSING_SCORE = 11

    # --- Mastery Algorithm ---
    MASTERY_THRESHOLD = 3  # Correct answers in a row to consider "Mastered"
    NEW_RATIO = 0.6  # 60% New/Unseen, 40% Review in Daily Sprint

    # --- Categories ---
    # We define these here to ensure consistency across the app
    CATEGORIES = [
        "Prawo i Dozór Techniczny",
        "Bezpieczeństwo i Organizacja Pracy",
        "Budowa i Parametry Techniczne",
        "Diagramy Udźwigu i Ładunki",
        "Napęd i Zasilanie",
        "Wyposażenie i Kontrolki",
    ]
