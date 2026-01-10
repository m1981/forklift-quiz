System Startup & Data Seeding
This process happens automatically when the app starts. It ensures the database is ready and populated with your 250 questions.
```mermaid
sequenceDiagram
    participant App as 🖥️ Streamlit UI
    participant Service as ⚙️ QuizService
    participant Repo as 🗄️ Repository
    participant DB as 💾 SQLite DB
    participant File as 📄 JSON File

    Note over App, DB: Application Startup
    App->>Service: get_service() (Cached)
    Service->>Repo: Initialize Repository
    Repo->>DB: CREATE TABLE IF NOT EXISTS
    
    App->>Service: initialize_db_from_file("seed.json")
    Service->>File: Load JSON Data
    File-->>Service: Return List[Question]
    Service->>Repo: seed_questions(List[Question])
    
    loop For each Question
        Repo->>DB: INSERT OR REPLACE INTO questions
    end
    
    DB-->>Repo: Success
    Repo-->>Service: Success
    Service-->>App: Ready
```

---

2. The Learning Flow (Standard Quiz)
This represents Use Case 1. It shows how a user interacts with the UI, how the answer is processed, and how persistence is handled immediately.
```mermaid
sequenceDiagram
    actor User as 👤 Learner
    participant App as 🖥️ Streamlit UI
    participant Service as ⚙️ QuizService
    participant Repo as 🗄️ Repository
    participant DB as 💾 SQLite DB

    Note over User, DB: Mode: Standard Quiz
    
    User->>App: Selects "Standard Mode" & "User A"
    App->>Service: get_quiz_questions("Standard", "User A")
    Service->>Repo: get_all_questions()
    Repo->>DB: SELECT * FROM questions
    DB-->>Repo: Return JSON Data
    Repo-->>Service: Return List[Question]
    Service-->>App: Return Full Question List

    App->>User: Display Question Q184 + Options

    User->>App: Clicks Answer Button "B"
    Note right of User: Triggers handle_answer() callback
    
    App->>Service: submit_answer("User A", Q184, "B")
    
    rect rgb(240, 248, 255)
        Note right of Service: Validation Logic
        Service->>Service: Check if "B" == correct_option
    end

    Service->>Repo: save_attempt("User A", Q184, is_correct=True)
    Repo->>DB: UPSERT into user_progress
    DB-->>Repo: Acknowledge Write
    
    Service-->>App: Return True (Correct)
    
    App->>User: Show "✅ Correct" Feedback & Explanation
    App->>User: Show "Next Question" Button 
```

---
3. The Repeating Flow (Smart Review)
This represents Use Case 2. It visualizes how the system filters data to help the user learn from mistakes.
```mermaid
sequenceDiagram
    actor User as 👤 Learner
    participant App as 🖥️ Streamlit UI
    participant Service as ⚙️ QuizService
    participant Repo as 🗄️ Repository
    participant DB as 💾 SQLite DB

    Note over User, DB: Mode: Review (Struggling Only)

    User->>App: Selects "Review Mode"
    App->>Service: get_quiz_questions("Review", "User A")
    
    rect rgb(255, 240, 240)
        Note right of Service: Filtering Logic
        Service->>Repo: get_all_questions()
        Repo-->>Service: [Q1, Q2, ... Q250]
        
        Service->>Repo: get_incorrect_question_ids("User A")
        Repo->>DB: SELECT question_id FROM user_progress WHERE is_correct=0
        DB-->>Repo: Return ["184", "205"]
        Repo-->>Service: Return ["184", "205"]
        
        Service->>Service: Filter List -> Only Q184, Q205
    end
    
    Service-->>App: Return Filtered List [Q184, Q205]
    
    App->>User: Display Q184 (Struggling Question)
    
    User->>App: Clicks Correct Answer
    App->>Service: submit_answer("User A", Q184, Correct)
    Service->>Repo: save_attempt("User A", Q184, True)
    Repo->>DB: UPDATE user_progress SET is_correct=1
    
    Note over DB: Q184 is now marked 'Correct'.<br/>It will not appear in the next Review Session.
    
    Service-->>App: Return Success
    App->>User: Show Feedback

```


### 4. Mermaid Sequence Diagram

This diagram now visualizes the decision logic inside the `seed_questions` method.

```mermaid
sequenceDiagram
    participant App as 🖥️ App Startup
    participant Repo as 🗄️ Repository
    participant DB as 💾 SQLite DB
    
    App->>Repo: seed_questions(New_List)
    Repo->>DB: SELECT * FROM questions
    DB-->>Repo: Return Existing_Map {id: Question}
    
    loop For Each New Question (NewQ)
        Repo->>Repo: Lookup OldQ = Existing_Map.get(NewQ.id)
        
        alt OldQ exists AND Answer Key Changed
            Note right of Repo: CRITICAL CHANGE DETECTED
            Repo->>DB: DELETE FROM user_progress WHERE question_id = NewQ.id
            Note right of DB: User history wiped for this Q
        end
        
        Repo->>DB: INSERT OR REPLACE INTO questions ...
    end
    
    DB-->>Repo: Commit Transaction
    Repo-->>App: Ready
```
