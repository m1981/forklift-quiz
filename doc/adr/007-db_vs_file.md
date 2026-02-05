# ADR 007: Content Storage Strategy (Database vs. File-Based)

**Status:** Accepted
**Date:** 2025-01-28
**Context:**
The application serves a static set of exam questions (Text, Options, Hints, Explanations) that are the same for all users.
We considered two approaches for storing and accessing this content:
1.  **File-Based (In-Memory):** Load `questions.json` into Python memory on startup. The Database stores only User Progress (`user_id`, `question_id`, `score`).
2.  **Database-Based (Current):** Store questions in a `questions` table (SQLite/Supabase). The Application queries content via SQL.

**Decision:**
We will **retain the Database-Based approach** (Option 2) and continue storing question content in the database.

**Rationale:**
1.  **Complex Querying Requirements:** The "Smart Mix" (Spaced Repetition) algorithm requires filtering questions based on a combination of *static metadata* (Category) and *dynamic user state* (Streak, Last Seen). Performing this `JOIN` operation in the database is significantly more performant and architecturally cleaner than fetching all user history into the Application layer to perform in-memory filtering against a JSON list.
2.  **Analytics Capabilities:** Storing content alongside progress allows for powerful SQL-based analytics (e.g., "Identify the hardest questions in the 'BHP' category"). This would require complex ETL processes if data were split between JSON files and the DB.
3.  **Scalability:** While the current dataset is small (~500 questions), a file-based approach loads *all* content into RAM. A database approach fetches only the necessary subset (e.g., 15 questions for a sprint), ensuring the application's memory footprint remains stable regardless of content growth.
4.  **Data Integrity:** Using a database allows us to (eventually) enforce Foreign Key constraints, ensuring that user progress records cannot exist for deleted or invalid question IDs.

**Consequences:**
*   **Positive:** We retain the ability to perform complex SQL queries and analytics. The application memory usage remains low.
*   **Negative:** We must maintain the `DataSeeder` and "Upsert" logic to keep the Database synchronized with the source JSON file during deployments.
*   **Mitigation:** We have implemented a "Force Seed" mechanism (ADR 004 update) to ensure content updates are reliably propagated to the database.

---
