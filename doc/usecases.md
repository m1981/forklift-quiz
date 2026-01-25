Below are the **Cockburn-style Use Cases** designed specifically for your Streamlit Quiz App. I have broken them down into the logical flows required to build a commercial-grade application.

---

### 1. Use Case: Take a Standard Quiz
**Level:** 🌊 Sea-level (User Goal)
**Primary Actor:** Learner
**Scope:** Streamlit Quiz Application
**Preconditions:** The application has loaded the 250-question dataset successfully.

**Main Success Scenario:**
1. Learner starts a new quiz session.
2. System initializes the score and retrieves the full list of questions.
3. System displays the first question with four options (A, B, C, D).
4. Learner selects an option and submits the answer.
5. System validates the answer against the key.
6. System provides immediate feedback (Correct/Incorrect) and explanation.
7. System records the result for that specific question ID in the session history.
8. Learner requests the next question.
9. System repeats steps 3-8 until the user decides to finish or questions run out.
10. Learner chooses to finish the quiz.
11. System displays the final score summary.

**Extensions:**
*   *1a. No questions available in dataset:*
    *   1a1. System displays an error message regarding data integrity.
    *   1a2. Use case ends failure.
*   *4a. Learner attempts to proceed without selecting an option:*
    *   4a1. System disables the "Submit" action or displays a prompt to select an option.
    *   4a2. Resume at step 4.
*   *10a. Learner finishes quiz before answering all questions:*
    *   10a1. System calculates score based only on answered questions.
    *   10a2. Resume at step 11.

**Success Guarantee:** The user has completed a set of questions, and the system has an in-memory record of which specific questions were answered correctly and incorrectly.

---

### 2. Use Case: Review Struggling Questions (The "Smart Review")
**Level:** 🌊 Sea-level (User Goal)
**Primary Actor:** Learner
**Scope:** Streamlit Quiz Application
**Preconditions:** User has completed at least one "Standard Quiz" session and answered at least one question incorrectly.

**Main Success Scenario:**
1. Learner selects "Review Missed Questions" mode.
2. System filters the question bank to include only questions marked as "Incorrect" in the session history.
3. System displays the count of struggling questions to be reviewed.
4. System presents a struggling question.
5. Learner submits an answer.
6. System validates the answer.
7. System updates the status of that question (removes from "struggling" list if correct).
8. System provides feedback.
9. Learner proceeds to the next struggling question.
10. System repeats steps 4-9 until the "struggling" queue is empty.
11. System displays a "All Caught Up" success message.

**Extensions:**
*   *2a. No incorrect answers found in history:*
    *   2a1. System displays a "Perfect Score / No History" notification.
    *   2a2. System suggests starting a Standard Quiz.
    *   2a3. Use case ends.
*   *7a. Learner answers incorrectly again:*
    *   7a1. System keeps the question in the "struggling" queue.
    *   7a2. System displays the correct answer and a detailed explanation to reinforce learning.
    *   7a3. Resume at step 9.

**Success Guarantee:** The user has re-attempted previously failed questions, and the system has updated the internal tracking to reflect improved knowledge.

---

### 3. Use Case: Reset Progress
**Level:** 🐟 Fish (Sub-function)
**Primary Actor:** Learner
**Scope:** Streamlit Quiz Application
**Preconditions:** User has active session history (scores/answers).

**Main Success Scenario:**
1. Learner selects "Reset Quiz" or "Clear History."
2. System requests confirmation to prevent accidental data loss.
3. Learner confirms the reset.
4. System clears all session state variables (score, incorrect question IDs, current question index).
5. System reloads the original question dataset.
6. System returns the interface to the "Start Screen" state.

**Extensions:**
*   *3a. Learner cancels the reset:*
    *   3a1. System closes the confirmation dialog.
    *   3a2. System retains current progress.
    *   3a3. Use case ends.

**Success Guarantee:** The application state is wiped clean, simulating a fresh page load.

---

#### 4. Use Case: System Maintenance (Smart Seeding)
**Level:** 🐟 Fish (Sub-function)
**Primary Actor:** System (Automatic on Startup)
**Scope:** Repository Layer

**Main Success Scenario:**
1. System loads the `seed_questions.json` file.
2. System retrieves existing questions from the database.
3. System iterates through each new question.
4. System detects that the `correct_option` matches the existing record (or record is new).
5. System updates the question definition (Text, Images, Options).
6. System preserves existing user progress.

**Extensions:**
*   *4a. Critical Data Change Detected:*
    *   4a1. System detects `correct_option` in JSON differs from Database.
    *   4a2. System deletes all records in `user_progress` table matching this `question_id`.
    *   4a3. System logs a warning: "Answer key changed. Progress reset."
    *   4a4. Resume at step 5.

---


### Technical Implementation Notes (Streamlit Specifics)

As a Streamlit expert, here is how I would map these use cases to code structures:

1.  **State Management (`st.session_state`):**
    *   We need a set or list called `st.session_state['incorrect_ids']`.
    *   When **Use Case 1, Step 5** happens (validation), if the answer is wrong, we `.add()` the ID to that set.
    *   When **Use Case 2, Step 7** happens (review success), we `.remove()` the ID from that set.

2.  **Data Structure:**
    *   The 250 questions should be loaded into a Pandas DataFrame or a list of dictionaries.
    *   `id`: Unique identifier (Crucial for tracking).
    *   `question`: String.
    *   `options`: List `['A', 'B', 'C', 'D']`.
    *   `answer`: String (e.g., 'A').
    *   `explanation`: String (Optional, but great for Step 6 in Use Case 1).

3.  **UI Layout:**
    *   Use `st.radio` for the options.
    *   Use `st.form` and `st.form_submit_button` to prevent the app from reloading immediately when a user clicks a radio button (this is a common Streamlit pitfall; we want them to click "Submit" explicitly).
