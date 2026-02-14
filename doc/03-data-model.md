# 3. Data Model (The "Truth")

## 3.1. Database Schema (Relational)

The application uses a hybrid relational/document approach. Core entities are relational tables, but complex question data is stored as JSON to allow flexible schema evolution (e.g., adding new languages or fields without migration headaches).

### A. `questions` Table
*   **Purpose:** Stores the static content of the quiz (text, options, translations).
*   **Primary Key:** `id` (String, e.g., "1", "2", "TUT-01").

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `TEXT` | Unique identifier for the question. Matches the source JSON ID. |
| `category` | `TEXT` | High-level grouping (e.g., "BHP", "Diagramy"). Used for filtering. |
| `json_data` | `JSON/TEXT` | **The Payload.** Contains the full `Question` object serialization. |

### B. `user_profiles` Table
*   **Purpose:** Stores user settings, preferences, and global state.
*   **Primary Key:** `user_id` (String, e.g., "User1", UUID).

| Column | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | `TEXT` | - | Unique user identifier. |
| `preferred_language` | `TEXT` | `'pl'` | Current UI/Hint language code (e.g., 'en', 'uk'). |
| `has_completed_onboarding` | `BOOLEAN` | `FALSE` | Flag to trigger the tutorial flow on first launch. |
| `streak_days` | `INTEGER` | `0` | (Gamification) Consecutive days the user has logged in. |
| `last_login` | `DATE` | `TODAY` | Used to calculate the daily streak. |
| `daily_goal` | `INTEGER` | `3` | Target number of sprints per day. |
| `daily_progress` | `INTEGER` | `0` | Number of sprints completed today. |
| `last_daily_reset` | `DATE` | `TODAY` | Timestamp for resetting `daily_progress`. |
| `metadata` | `JSON/TEXT` | `{}` | Flexible field. In Demo mode, stores `{"type": "demo", "prospect": "slug"}` for analytics. |
### C. `user_progress` Table
*   **Purpose:** The core learning record. Tracks every interaction between a user and a question.
*   **Primary Key:** Composite (`user_id`, `question_id`).

| Column | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `user_id` | `TEXT` | - | Foreign Key to `user_profiles`. |
| `question_id` | `TEXT` | - | Foreign Key to `questions`. |
| `is_correct` | `BOOLEAN` | - | Result of the **last** attempt. |
| `consecutive_correct` | `INTEGER` | `0` | **The Mastery Metric.** Resets to 0 on error, increments on success. |
| `timestamp` | `DATETIME` | `NOW` | Time of the last attempt. Used for Spaced Repetition aging. |

---

## 3.2. Domain Objects (Application Layer)

These Pydantic models define how data is handled within the Python code (`src/quiz/domain/models.py`).

### A. `Question` Entity
This object represents the deserialized `json_data` from the database.

```json
{
  "id": "15",
  "text": "Jaki jest maksymalny udźwig wózka?",
  "category": "Parametry Techniczne",
  "image_path": "assets/images/q15.png",
  "options": {
    "A": "1000 kg",
    "B": "1500 kg",
    "C": "2000 kg"
  },
  "correct_option": "B",
  "explanation": "Tabliczka znamionowa określa udźwig nominalny.",
  "hint": "Spójrz na wykres udźwigu.",
  "translations": {
    "en": {
      "explanation": "The rating plate defines the nominal capacity.",
      "hint": "Look at the load chart."
    },
    "uk": {
      "explanation": "...",
      "hint": "..."
    }
  }
}
```

### B. `UserProfile` Entity
Represents the active user's session context.

```python
class UserProfile(BaseModel):
    user_id: str
    preferred_language: Language = Language.PL
    has_completed_onboarding: bool = False
    # ... gamification fields ...
```

### C. `QuestionCandidate` (DTO)
Used specifically by the **Spaced Repetition Algorithm** to weigh questions for selection.

```python
@dataclass
class QuestionCandidate:
    question: Question
    streak: int      # From user_progress.consecutive_correct
    is_seen: bool    # True if user_progress record exists
```

---

## 3.3. Data Integrity & Constraints

1.  **Source of Truth:** The `questions` table is read-only for the application. Updates happen via the `data/` scripts (seeding), not user interaction.
2.  **Language Fallback:**
    *   The `text` and `options` fields in `Question` are **always Polish**.
    *   `explanation` and `hint` have localized overrides in the `translations` dictionary.
    *   If a requested language is missing in `translations`, the system **must** fall back to the root Polish fields.
3.  **Persistence Strategy:**
    *   **User Preferences (Language):** Persisted **immediately** on change (write-through).
    *   **Quiz Progress:** Persisted **per question** (after every "Submit Answer" click). This ensures that if a user closes the browser mid-quiz, their progress on specific questions is saved, even if the "Sprint" session is lost.
