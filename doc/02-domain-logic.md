# 2. Domain Logic (The "Rules")

## 2.1. Spaced Repetition Algorithm (The "Smart Mix")
The core value proposition of the app is the **Spaced Repetition System (SRS)**. It ensures users learn efficiently by prioritizing questions they struggle with while maintaining retention of mastered topics.

### A. Question Pools
The algorithm categorizes all available questions into three pools based on the user's history:

1.  **New Pool:** Questions the user has **never seen** (`is_seen = False`).
2.  **Learning Pool:** Questions seen before but **not yet mastered** (`streak < MASTERY_THRESHOLD`).
3.  **Review Pool:** Questions currently **mastered** (`streak >= MASTERY_THRESHOLD`).

### B. Selection Logic (Daily Sprint)
When a user starts a "Daily Sprint" (15 questions), the `SpacedRepetitionSelector` builds the quiz using the following priority mix:

1.  **Review Priority:** First, it looks for **Review** questions that haven't been seen in at least **3 days**. This prevents "over-practicing" known material.
2.  **Learning Priority:** Next, it fills the quota with **Learning** questions (the "struggle zone").
3.  **New Content:** Finally, it fills the remaining slots with **New** questions (approx. 60% of the sprint, configurable via `NEW_RATIO`).
4.  **Backfill:** If there aren't enough New/Review questions, it falls back to random Learning questions to ensure the user always gets a full 15-question set.

---

## 2.2. Mastery & Progression Rules

### A. Mastery Definition
A question is considered **"Mastered"** when the user answers it correctly **consecutively** a specific number of times.
*   **Threshold:** Defined in `GameConfig.MASTERY_THRESHOLD` (Default: **3**).
*   **Logic:**
    *   Correct Answer $\rightarrow$ `streak + 1`
    *   Incorrect Answer $\rightarrow$ `streak = 0` (Immediate reset to ensure relearning).

### B. Global Progress
*   **Calculation:** `Total Mastered Questions / Total Questions in Database`.
*   **Visuals:** Displayed as a progress bar on the Dashboard and Hero component.
*   **Completion Date:** Estimated based on the remaining unmastered questions divided by the daily sprint size (e.g., `Remaining / 15`).

---

## 2.3. Quiz Session Rules

### A. Feedback Loop
The quiz operates in two modes per question:
1.  **Active Mode:** The user sees the question and options. No feedback is shown.
2.  **Feedback Mode:** Immediately after submission:
    *   The selected option is highlighted.
    *   If wrong, the correct option is highlighted in Green, selected in Red.
    *   **Explanation:** A detailed explanation is revealed.
    *   **Translation:** If the user's language is not Polish, the explanation is translated (if available), with an option to view the original Polish text.

### B. Scoring
*   **Correct Answer:** +1 Point.
*   **Incorrect Answer:** +0 Points.
*   **Passing Score:** Defined in `GameConfig.PASSING_SCORE` (Default: **11/15** or ~73%).

### C. Error Review ("Poprawa Błędów")
*   **Trigger:** If a user makes mistakes during a sprint, the Summary screen offers a "Fix Mistakes" button.
*   **Behavior:** A new, temporary quiz session is generated containing **only** the questions answered incorrectly in the immediate previous session.
*   **Scoring:** Answers in this mode **do** update the database (streak reset/increment) but do not affect the score of the *previous* sprint.

---

## 2.4. Localization & Language Rules

### A. Source of Truth
*   **Polish (PL):** The canonical language for all Questions, Options, and Exam Regulations.
*   **Behavior:** The Question Text and Options are **always** displayed in Polish to simulate the real UDT exam environment.

### B. Assistance (Hints & Explanations)
*   **User Preference:** Stored in `UserProfile.preferred_language`.
*   **Fallback Strategy:**
    1.  Check if a translation exists for the user's preferred language.
    2.  If **Yes**: Display the translated content.
    3.  If **No**: Fallback to Polish.
*   **UI Toggle:** Users can switch the language of a specific Hint/Explanation on the fly using "Pills". This selection is **persisted immediately** to the database as their new preference.

---

## 2.5. Onboarding Flow
*   **Trigger:** Occurs only if `UserProfile.has_completed_onboarding` is `False`.
*   **Content:** A single, hardcoded "Tutorial" question (`ID: TUT-01`).
*   **Outcome:**
    *   User learns UI mechanics (selecting, submitting, reading feedback).
    *   Upon completion, the `has_completed_onboarding` flag is set to `True`.
    *   User is redirected to the Dashboard.

## 2.6. Demo Mode Constraints
*   **Content:** Demo users have access to the full question database (no restrictions).
*   **State:**
    *   Demo progress is saved to the database under the `demo_{slug}` user ID.
    *   This allows the sales team to "pre-warm" a demo account with some progress if desired, or reset it by clearing that specific user ID in the DB.
*   **Logo Fallback:** If `assets/logos/{slug}.png` does not exist, the system silently falls back to the default application logo (`assets/logo.jpg`).
