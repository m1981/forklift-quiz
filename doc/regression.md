Here is a comprehensive **Regression Test Suite** documenting the issues we resolved. These scenarios are designed for your QA team to validate that the fixes are robust and the application behaves consistently.

---

# 🧪 Regression Test Scenarios: Warehouse Quiz App

**Application Version:** 2.0 (FSM & Clean Architecture)
**Framework:** Streamlit
**Database:** SQLite

---

## 1. Scenario: Daily Goal Integrity (The "Farming" Bug)
**Background:** Previously, users could spam the same question repeatedly to artificially inflate their "Daily Goal" progress (e.g., answering 1 question 10 times resulted in 10/3 progress).
**Objective:** Verify that only *unique* questions answered *today* count towards the daily goal.

| Step | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- |
| 1 | Click "Zeruj postęp" (Reset Progress) in the sidebar. | App resets. Dashboard shows "Cel: 0/3". | |
| 2 | Start "Codzienny Sprint". | Question 1 appears. | |
| 3 | Answer Question 1 correctly. | Feedback shows "✅ Dobrze!". Dashboard updates to "Cel: **1**/3". | |
| 4 | Click "Następne" until the quiz finishes. | Summary screen appears. | |
| 5 | Click "Wróć do Menu" and Start "Codzienny Sprint" again. | App loads a new set of questions. | |
| 6 | **Critical Step:** If Question 1 appears again (or any question answered in Step 3), answer it again. | Feedback shows result. Dashboard **remains at "Cel: 1/3"** (or whatever the count was before this specific question). It must **NOT** increment for a duplicate attempt today. | |

---

## 2. Scenario: Mode Switching Stability (The "Ghost Reset" Bug)
**Background:** Previously, switching from "Sprint" to "Review" caused the internal state to reset to IDLE but sometimes failed to load the correct question set, or required multiple clicks to register the mode change.
**Objective:** Verify that switching modes immediately resets the game state and prepares the correct environment.

| Step | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- |
| 1 | Select "Codzienny Sprint" and click "Start". | Quiz starts. Questions are loaded. | |
| 2 | Answer 1 question incorrectly (to ensure Review mode has data). | Feedback shows "❌ Źle". | |
| 3 | **Critical Step:** Immediately change the Sidebar Radio Button to "Powtórka (Błędy)". | The main screen **immediately** resets to the "Welcome/Start" screen. The text above the button updates to "**Wybrany tryb: Powtórka (Błędy)**". | |
| 4 | Click "Rozpocznij Quiz". | The quiz loads **only** the incorrect question(s) from Step 2. The header shows "🛠️ Tryb Poprawy Błędów". | |

---

## 3. Scenario: User Identity Isolation (The "Split Personality" Bug)
**Background:** Previously, switching the User in the sidebar did not clear the session state. The Debugger would show stats for "User B" while the main screen displayed questions/progress for "User A".
**Objective:** Verify that changing the user completely wipes the session and loads the new user's profile.

| Step | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- |
| 1 | Select User: **Daniel**. Reset Progress. | Dashboard shows "Seria: 0". | |
| 2 | Start Sprint, answer 1 question correctly. | Dashboard shows "Cel: 1/3". | |
| 3 | **Critical Step:** Change Sidebar User to **Michał**. | The app **immediately** reloads/resets to the Start Screen. | |
| 4 | Open "Debugger Danych" in sidebar. | "User" should read **Michał**. "Total Records" should be **0** (assuming Michał is new/reset). | |
| 5 | Switch back to **Daniel**. | App resets. Dashboard (after clicking Start) should recover the "Cel: 1/3" progress from Step 2. | |

---

## 4. Scenario: Review Mode Logic (The "Empty State" Bug)
**Background:** Previously, if a user had errors in the database, the app sometimes failed to load them because of type mismatches (String vs Integer IDs) or state caching issues, showing "No questions" incorrectly.
**Objective:** Verify that Review Mode accurately reflects the database state.

| Step | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- |
| 1 | Ensure "Debugger Danych" shows `Incorrect (0): 0`. | If not 0, click Reset Progress. | |
| 2 | Select "Powtórka (Błędy)". | The Start Screen should display a green success message: "🎉 Brak błędów do poprawy! Przełącz na Sprint." | |
| 3 | Switch to Sprint. Answer 1 question **Incorrectly**. | Feedback shows Red X. | |
| 4 | Switch back to "Powtórka (Błędy)". | The Start Screen should now display a warning: "⚠️ Masz **1** błędów do poprawy." | |
| 5 | Click Start. | The specific question missed in Step 3 appears. The header is Red/Warning style. | |
| 6 | Answer Correctly. | Feedback shows Green Check. | |
| 7 | Finish Quiz and return to Menu. | The Start Screen should now say "🎉 Brak błędów do poprawy!". | |

---

## 5. Scenario: Visual Feedback Persistence (The "Disappearing Options" Bug)
**Background:** Previously, clicking an answer button caused the options to disappear immediately, replaced by the explanation. Users could not compare their choice with the correct answer.
**Objective:** Verify that the "Frozen" state displays correctly.

| Step | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- |
| 1 | Start any quiz. | Question appears with clickable buttons (A, B, C, D). | |
| 2 | Click a **Wrong** answer (e.g., B). | 1. Buttons disappear.<br>2. A static list appears.<br>3. Option B is marked with ❌ and **Red Bold** text.<br>4. The Correct Option (e.g., A) is marked with ✅ and **Green Bold** text.<br>5. Explanation box appears below. | |
| 3 | Click "Następne". | New question appears with clickable buttons. | |

---

## 6. Scenario: Summary Screen Auto-Jump (The "Race Condition" Bug)
**Background:** Previously, answering the last question immediately triggered the "Summary/Balloons" screen, preventing the user from reading the explanation for the final question.
**Objective:** Verify the manual finish step.

| Step | Action | Expected Result | Pass/Fail |
| :--- | :--- | :--- | :--- |
| 1 | Start a quiz (Sprint or Review). | Quiz active. | |
| 2 | Navigate to the **Last Question** (e.g., 3/3 or 10/10). | Question appears. | |
| 3 | Submit an answer. | **The Summary screen must NOT appear yet.** The user must see the Feedback/Frozen Options for this last question. | |
| 4 | Verify the navigation button label. | The button should read **"Podsumowanie 🏁"** (not "Następne"). | |
| 5 | Click "Podsumowanie 🏁". | **Now** the Summary screen (Balloons/Score) appears. | |
