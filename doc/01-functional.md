# Warehouse Certification Adaptive Learning Platform
**System Specification**

## 1. Domain Understanding & Scope

**Context:**
The application is an adaptive learning platform designed to prepare warehouse staff (specifically forklift operators) for technical certification exams (UDT). Unlike a static quiz, the system employs **Spaced Repetition** to optimize retention.

**Core Value Proposition:**
1.  **Efficiency:** Users do not waste time answering questions they already know perfectly.
2.  **Retention:** The system re-introduces "mastered" questions after a decay period to ensure long-term memory.
3.  **Habit Formation:** Gamification elements (Streaks, Daily Goals) encourage small, daily learning sessions rather than "cramming."

**In/Out Scope List:**
*   **IN:** Mobile-first interface, Spaced Repetition logic, Daily Sprints, Category Reviews, Mistake Correction, Basic Gamification (Streaks).
*   **OUT:** Social leaderboards, Instructor dashboard, Content authoring tools (content is pre-loaded), Payment processing.

---

## 2. Domain Glossary (Ubiquitous Language)

| Term | Definition |
| :--- | :--- |
| **Sprint** | A single game session consisting of a fixed number of questions (default: 15). |
| **Mastery** | The state of a question where the user has answered it correctly `N` times in a row. |
| **Streak (User)** | The number of consecutive days a user has logged in. |
| **Streak (Question)** | The number of times a specific question has been answered correctly *in a row*. Resets to 0 on failure. |
| **Smart Mix** | The algorithmically generated set of questions for a Daily Sprint balancing New vs. Review material. |
| **Decay** | The logic that forces a "Mastered" question back into the review pool after a set time. |

---

## 3. Business Rules (The "Spokes")

*These rules are referenced by the Use Cases but kept separate to keep the narrative clean.*

**BR-01: The Smart Mix Algorithm**
The system selects questions based on the following priority:
1.  **New Pool:** Questions never seen.
2.  **Learning Pool:** Seen questions with `question_streak < MASTERY_THRESHOLD`.
3.  **Review Pool:** Seen questions with `question_streak >= MASTERY_THRESHOLD` AND `last_seen > 3 days ago`.
*Target Ratio:* 60% New / 40% Review. If "New" is empty, backfill with Review.

**BR-02: Scoring & Mastery**
*   **Mastery Threshold:** A question is "Mastered" when `consecutive_correct >= 1`.
*   **High Stakes Reset:** If a user answers incorrectly, `consecutive_correct` resets to **0** immediately.
*   **Passing Score:** A Sprint is "Passed" if the score is $\ge 11/15$ (~73%).

**BR-03: User Streak Logic**
*   Login on $Today = LastLogin + 1$: Streak increments (+1).
*   Login on $Today > LastLogin + 1$: Streak resets to 1.

---

## 4. Primary Actors & Goals

| Actor | Goal | Level |
| :--- | :--- | :--- |
| **Forklift Operator** | Complete a Daily Sprint | 🌊 User Goal |
| **Forklift Operator** | Review a Specific Category | 🌊 User Goal |
| **Forklift Operator** | Fix Mistakes from Previous Session | 🌊 User Goal |
| **New User** | Onboard to the Platform | 🌊 User Goal |

---

## 5. Use Cases (The "Hubs")

### Use Case 1: Complete Daily Sprint

**Primary Actor:** Forklift Operator
**Scope:** Warehouse Quiz App
**Level:** 🌊 User Goal
**Trigger:** User selects "Start Daily Sprint" from the Dashboard.

**Preconditions:** User is logged in.
**Minimal Guarantees:** System saves the result of every individual question answered, even if the sprint is aborted.
**Success Guarantees:** Sprint is marked complete. Daily Goal counter increments. Question weights are updated for tomorrow.

**Main Success Scenario (MSS):**
1.  System generates a "Smart Mix" of questions based on **BR-01**.
2.  **User and System repeat until sprint limit is reached:**
    a. System presents the next question.
    b. User submits an answer.
    c. System validates the answer and records the result (Pass/Fail) to the database.
    d. System provides immediate feedback on correctness.
3.  System calculates the final score based on **BR-02**.
4.  System presents the Sprint Summary (score, time, rewards).
5.  User acknowledges the summary to return to the Dashboard.

**Extensions:**
*   **1a. Insufficient Questions:**
    *   1a1. System detects fewer than 15 eligible questions.
    *   1a2. System generates a reduced-length sprint.
*   **1b. No Questions Available (All Mastered):**
    *   1b1. System detects 0 eligible questions.
    *   1b2. System informs user they are up to date.
    *   1b3. Use case ends (Success).
*   **2a. User Aborts (e.g., closes app):**
    *   2a1. System saves progress of *answered* questions.
    *   2a2. System discards the session completion status.
    *   2a3. Use case ends (Fail).

---

### Use Case 2: Review Specific Category

**Primary Actor:** Forklift Operator
**Scope:** Warehouse Quiz App
**Level:** 🌊 User Goal
**Trigger:** User selects a specific category (e.g., "Safety") from the Library.

**Preconditions:** User is on the Dashboard.
**Success Guarantees:** User has practiced questions exclusively from the selected domain.

**Main Success Scenario (MSS):**
1.  System retrieves all eligible questions for the selected category.
2.  **User and System repeat until all questions in category are answered OR user stops:**
    a. System presents the next question.
    b. User submits an answer.
    c. System validates and records the result.
    d. System provides immediate feedback.
3.  System presents the Summary Screen.
4.  User acknowledges the summary to return to the Dashboard.

**Extensions:**
*   **1a. Category Empty:**
    *   1a1. System displays "No questions in category" message.
    *   1a2. User returns to Dashboard.

---

### Use Case 3: Fix Mistakes

**Primary Actor:** Forklift Operator
**Scope:** Warehouse Quiz App
**Level:** 🌊 User Goal
**Trigger:** User selects "Fix Mistakes" from the Summary Screen.

**Preconditions:**
*   User has just completed a Sprint.
*   The session resulted in at least one incorrect answer.

**Success Guarantees:** All errors from the previous session have been reviewed and re-attempted.

**Main Success Scenario (MSS):**
1.  System retrieves the list of failed questions from the immediate previous session.
2.  **User and System repeat until all errors are reviewed:**
    a. System presents the failed question.
    b. User submits the correct answer.
    c. System updates DB (streak moves from 0 -> 1).
    d. System displays positive feedback.
3.  System presents the Summary Screen.

**Extensions:**
*   **2b. User selects the INCORRECT answer (again):**
    *   2b1. System records the failure (streak remains 0).
    *   2b2. System displays negative feedback.
    *   2b3. System moves to the next question (does **not** force an immediate retry).

---

### Use Case 4: Onboard New User

**Primary Actor:** New User
**Scope:** Warehouse Quiz App
**Level:** 🌊 User Goal
**Trigger:** User logs in for the first time.

**Preconditions:** `has_completed_onboarding` is False.
**Success Guarantees:** User understands UI mechanics; `has_completed_onboarding` is set to True.

**Main Success Scenario (MSS):**
1.  System displays the Welcome / Context screen.
2.  User proceeds to the Tutorial.
3.  System presents a sample Tutorial Question.
4.  User successfully completes the interaction (selects correct answer).
5.  System displays "Training Complete" confirmation.
6.  System updates profile: `has_completed_onboarding = True`.
7.  System redirects to Dashboard.

**Extensions:**
*   **4a. User answers incorrectly:**
    *   4a1. System displays error feedback (demonstrating the "Wrong Answer" UI).
    *   4a2. System prompts user to try again.
    *   4a3. Resume at Step 4.
