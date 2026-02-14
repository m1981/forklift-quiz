# 2. Domain Logic (The "Rules")

## 2.1. Spaced Repetition Algorithm (The "Smart Mix")
The core value proposition of the app is the **Spaced Repetition System (SRS)**. It ensures users learn efficiently by prioritizing questions they struggle with while maintaining retention of mastered topics.

### A. Question Pools
The algorithm categorizes all available questions into three pools based on the user's history:

1.  **New Pool:** Questions the user has **never seen** (`is_seen = False`).
2.  **Learning Pool:** Questions seen before but **not yet mastered** (`streak < MASTERY_THRESHOLD`).
3.  **Review Pool:** Questions currently **mastered** (`streak >= MASTERY_THRESHOLD`).

### B. Selection Logic (Daily Sprint)

#### Stage 1: Pool Segregation
The algorithm divides all eligible questions into 3 independent pools:
1.  **New Pool:** Questions never seen (`is_seen = False`).
2.  **Learning Pool:** Questions with `streak < MASTERY_THRESHOLD`.
3.  **Review Pool:** Questions with `streak >= MASTERY_THRESHOLD` AND `last_seen > 3 days`.

#### Stage 2: Independent Shuffling
Each pool is shuffled **independently** using `random.shuffle()` to ensure unpredictability.

#### Stage 3: Priority-Based Selection
1.  **Review Priority:** Select up to 40% from (Learning + Review) pools.
2.  **New Content:** Select up to 60% from New pool.
3.  **Backfill:** If New pool is empty, fill remaining slots from Learning/Review.

#### Stage 4: Final Shuffle
The selected 15 questions are shuffled **again** to hide the algorithm's pattern from users.

**Example:**
- Learning Pool: 20 questions → Shuffle → Take 6
- New Pool: 30 questions → Shuffle → Take 9
- Final Mix: 15 questions → Shuffle → Present to user

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

## 2.3. Category Mode Selection

### A. Purpose
Allows users to focus on a specific topic (e.g., "Diagramy Udźwigu") instead of the Smart Mix.

### B. Selection Logic
When a user starts Category Mode, the system:

1.  **Filters** all questions by the selected category.
2.  **Prioritizes** questions with the lowest `consecutive_correct` (weakest mastery).
3.  **Randomizes** among questions with equal mastery levels.
4.  **Returns** 15 questions (or fewer if category is small).

### C. Implementation
*   **Algorithm:** `CategorySelector.prioritize_weak_questions()`
*   **Sorting:** Primary key = `consecutive_correct ASC`, Secondary key = `RANDOM()`
*   **Consistency:** Both SQLite and Supabase use identical logic (as of v1.1.0).

### D. Difference from Daily Sprint
*   **No 60/40 New/Review split** (all questions from one category).
*   **No 3-day decay logic** (shows all eligible questions).
*   **Simpler algorithm** (prioritize weak, then random).

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

## 2.7. Performance Optimization: ProfileManager

### A. Problem Statement
Streamlit's reactive model reruns the entire script on every user interaction. Without optimization, this would cause:
*   **Excessive DB Reads:** Fetching `UserProfile` on every rerun (15+ times per quiz).
*   **Excessive DB Writes:** Saving `daily_progress` after every question (15 writes per quiz).

### B. Solution: Write-Through Cache with Batching
The `ProfileManager` class (`src/quiz/domain/profile_manager.py`) implements a caching layer:

1.  **Read Caching:** Profile is fetched once per session and stored in `st.session_state`.
2.  **Write Batching:** Non-critical updates are accumulated and flushed every 5 changes.
3.  **Immediate Flush:** Critical changes (language, onboarding, date reset) bypass batching.

### C. Performance Metrics
| Metric | Before | After | Improvement |
| :--- | :--- | :--- | :--- |
| DB Reads (15-question quiz) | 15 | 1 | 93% ↓ |
| DB Writes (15-question quiz) | 15 | 3 | 80% ↓ |
| Total DB Calls | 30 | 4 | 87% ↓ |

### D. Trade-offs
*   **Complexity:** Adds ~100 lines of code for caching logic.
*   **Risk:** If `flush()` is not called at session end, the last 1-4 changes may be lost (mitigated by auto-flush threshold).
*   **Benefit:** Significantly reduces database load, especially important for cloud-hosted databases (Supabase) where API calls are rate-limited.
