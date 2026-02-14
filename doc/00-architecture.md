# Architecture Overview

This document outlines the structural design of the Warehouse Quiz App. The application follows a **Service-Oriented Architecture (SOA)** adapted for Streamlit, emphasizing simplicity, direct state management, and a clean separation between UI, Business Logic, and Data.

---

## 1. System Architecture Diagram

The system is divided into three distinct layers. The **Presentation Layer** (Streamlit) interacts directly with the **Service Layer** (Business Logic), which in turn manages the **Data Layer** (Repositories).

```mermaid
graph TD
    subgraph Presentation["Presentation Layer (Streamlit)"]
        App["app.py<br/>(Router & Entry Point)"]
        Views["View Modules<br/>dashboard_view, question_view"]
        Components["Custom HTML/JS Components"]
        Session["st.session_state"]
    end

    subgraph Service["Service Layer (Business Logic)"]
        GameService["GameService"]
        Algo["SpacedRepetitionSelector"]
    end

    subgraph Data["Data Layer (Persistence)"]
        Repo["IQuizRepository<br/>(Interface)"]
        SQLiteRepo["SQLiteQuizRepository"]
        SupabaseRepo["SupabaseQuizRepository"]
        Models["Domain Models<br/>Question, UserProfile"]
    end

    %% Interactions
    App -->|Initializes| GameService
    App -->|Routes to| Views

    Views -->|Reads| Session
    Views -->|Calls Actions| GameService

    GameService -->|Updates| Session
    GameService -->|Uses| Algo
    GameService -->|Reads/Writes| Repo

    Repo -->|Returns| Models
    SQLiteRepo -.->|implements| Repo
    SupabaseRepo -.->|implements| Repo
```

---

## 2. Component Interaction Patterns

### 2.1. Streamlit-Native State Management
Instead of a custom "Director" or "Context" object, the application uses Streamlit's native `st.session_state` as the **Single Source of Truth** for transient UI state.
*   **Screen Routing:** `st.session_state.screen` determines which view function to call in `app.py`.
*   **Quiz State:** `st.session_state.quiz_questions`, `current_index`, and `score` track progress.
*   **Service Layer:** The `GameService` is responsible for mutating this state in response to user actions.

### 2.2. Service Layer Pattern
All business logic is encapsulated in `src/game/service.py`.
*   **Responsibility:** It handles rules for scoring, spaced repetition, onboarding, and database synchronization.
*   **Benefit:** The UI (Views) remains "dumb." It simply calls methods like `service.submit_answer()` or `service.start_daily_sprint()`.

### 2.3. Repository Pattern (Ports & Adapters)
The Domain layer defines *what* data operations are needed (`IQuizRepository`), but not *how* they are implemented.
*   **Port:** `src/quiz/domain/ports.py`
*   **Adapter:** `src/quiz/adapters/sqlite_repository.py`
*   **Benefit:** Allows seamless switching between SQLite (local dev) and Supabase (production) via configuration (`GameConfig.USE_SQLITE`).

### 2.4. The Demo Mode Pattern
To support sales demos without polluting production data:
*   **Trigger:** URL Parameter `?demo=slug` (e.g., `?demo=tesla`).
*   **Isolation:** `app.py` detects the parameter and generates a unique `user_id` (e.g., `demo_tesla`), ensuring isolated progress.
*   **Branding:** The `GameService` accepts the slug to dynamically resolve and inject custom logos into the Dashboard.

---

## 3. Core Business Processes

### 3.1. The "Smart Mix" Generation Process
This logic resides in `SpacedRepetitionSelector` and is called by `GameService.start_daily_sprint`.

```mermaid
flowchart TD
    Start([Start Daily Sprint]) --> Fetch[Fetch All Candidates from DB]
    Fetch --> Filter[Filter Logic]

    subgraph Filtering["Candidate Filtering (SQL)"]
        C1{Is New?}
        C2{Is Learning?<br/>Streak < Threshold}
        C3{Is Review?<br/>Streak >= Threshold AND<br/>LastSeen > 3 days}
    end

    Filter --> C1
    Filter --> C2
    Filter --> C3

    C1 --> PoolNew[New Pool]
    C2 --> PoolRev[Review/Learning Pool]
    C3 --> PoolRev

    PoolNew --> Calc[Calculate Targets<br/>Target: 60% New, 40% Review]
    PoolRev --> Calc

    Calc --> Select{Selection}
    Select -->|Fill Review| List[Selected Questions]
    Select -->|Fill New| List

    List --> Check{Not Full?}
    Check -->|Yes| Backfill[Backfill from remaining pools]
    Check -->|No| Shuffle[Random Shuffle]
    Backfill --> Shuffle
    Shuffle --> End([Return 15 Questions])
```

### 3.2. User Attempt & Mastery Update
This process describes the flow when a user answers a question.

```mermaid
sequenceDiagram
    participant User
    participant View as question_view.py
    participant Service as GameService
    participant Session as st.session_state
    participant DB as SQLiteRepository

    User->>View: Clicks Option "A"
    View->>Service: submit_answer(user, q, "A")

    Service->>Service: Check Correctness

    alt is Correct
        Service->>Session: score += 1
        Service->>DB: save_attempt(is_correct=True)
        DB->>DB: UPDATE user_progress<br/>SET consecutive_correct += 1
    else is Wrong
        Service->>Session: Add to Error List
        Service->>DB: save_attempt(is_correct=False)
        DB->>DB: UPDATE user_progress<br/>SET consecutive_correct = 0
    end

    Service->>Session: Set feedback_mode = True
    View->>User: Rerun & Show Feedback
```

### 3.3. Profile Synchronization (Login)
Logic found in `get_or_create_profile` to handle daily streaks.

```mermaid
flowchart LR
    Login([User App Open]) --> Fetch[Fetch Profile]
    Fetch --> CheckDate{Compare Today <br/>vs Last Login}

    CheckDate -->|Diff == 0| NoOp[Do Nothing]
    CheckDate -->|Diff == 1| Inc[Streak++]
    CheckDate -->|Diff > 1| Reset[Streak = 1]

    Inc --> Save[Save Profile]
    Reset --> Save
    NoOp --> Ready([Ready])
    Save --> Ready
```

---

## 4. Domain Model (Entity Relationships)

This diagram represents the logical data structure derived from `src/quiz/domain/models.py` and the SQLite schema.

```mermaid
erDiagram
    User ||--|| UserProfile : "has"
    User ||--o{ UserProgress : "attempts"
    Question ||--o{ UserProgress : "tracks"
    Question }|--|| Category : "belongs to"

    User {
        string user_id PK
    }

    UserProfile {
        string user_id FK
        int streak_days
        date last_login
        int daily_goal
        int daily_progress
        bool has_completed_onboarding
        string preferred_language
    }

    Question {
        string id PK
        string text
        string category
        json options
        string correct_option
        string explanation
        json translations
    }

    UserProgress {
        string user_id PK, FK
        string question_id PK, FK
        bool is_correct
        int consecutive_correct "Critical for Mastery"
        datetime timestamp "Used for Decay logic"
    }
```

---

## 5. Integration Points

### 5.1. Internal Integration (Persistence)
*   **SQLite File:** The app integrates with the local file system at `data/quiz.db`.
*   **Migration System:** The `DatabaseManager` performs schema checks on startup (`_init_schema`, `_migrate_schema`) to ensure the DB structure matches the code version.

### 5.2. External Integration (Observability)
*   **Telemetry:** The `src/shared/telemetry.py` module provides a wrapper for logging and metrics (Prometheus), allowing performance monitoring of database queries and service actions.

### 5.3. Entry Point Integration
*   **`app.py`:** Acts as the Composition Root. It initializes the Repository, seeds the database, creates the `GameService`, and sets up the User Session before routing to the appropriate View.
