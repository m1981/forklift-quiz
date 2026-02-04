

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
    }

    Question {
        string id PK
        string text
        string category
        json options
        string correct_option
        string explanation
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

## 5. Core Business Processes

### 5.1. The "Smart Mix" Generation Process
This is the most complex logic in the system, residing in `SpacedRepetitionSelector`.

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

### 5.2. User Attempt & Mastery Update
This process describes what happens when a user clicks an answer button.

```mermaid
sequenceDiagram
    participant User
    participant UI as QuestionView
    participant Engine as GameDirector
    participant DB as SQLiteRepository

    User->>UI: Selects Option "A"
    UI->>Engine: Action: SUBMIT_ANSWER("A")

    Engine->>Engine: Check Correctness

    alt is Correct
        Engine->>Engine: Session Score + 1
        Engine->>DB: save_attempt(is_correct=True)
        DB->>DB: UPDATE user_progress<br/>SET consecutive_correct += 1
    else is Wrong
        Engine->>Engine: Add to Error List
        Engine->>DB: save_attempt(is_correct=False)
        DB->>DB: UPDATE user_progress<br/>SET consecutive_correct = 0
    end

    Engine->>UI: Return Feedback Payload
    UI->>User: Show Green/Red Card & Explanation
```

### 5.3. Profile Synchronization (Login)
Logic found in `get_or_create_profile` to handle streaks.

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


Here is the **Architecture Overview** documentation package.

This document outlines the structural design of the Warehouse Quiz App. It highlights the transition from a standard script-based Streamlit app to a commercial-grade **Hexagonal Architecture** driven by a **State Machine**.

---

## 1. System Architecture Diagram

The system follows a strict **Layered Hexagonal Architecture** (Ports and Adapters). This ensures that the core business logic (Spaced Repetition, Scoring) is completely isolated from the UI framework (Streamlit) and the Database (SQLite).

```mermaid
graph TD
    subgraph Presentation["Presentation Layer (Streamlit)"]
        Browser[User Browser]
        StreamlitRuntime[Streamlit Runtime]
        Renderer[StreamlitRenderer]
        ViewModel[GameViewModel]
        Components[Custom HTML/JS Components]
    end

    subgraph Application["Application Layer (Game Engine)"]
        Director[GameDirector]
        Flows[GameFlows<br/>DailySprint, CategorySprint]
        Steps[GameSteps<br/>QuestionLoop, Dashboard]
        Context[GameContext<br/>Session State]
    end

    subgraph Domain["Domain Layer (Pure Python)"]
        Algo[SpacedRepetitionSelector]
        Models[Domain Models<br/>Question, UserProfile]
        Ports[Interface<br/>IQuizRepository]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        SQLiteRepo[SQLiteQuizRepository]
        SupabaseRepo[SupabaseQuizRepository]
        DBManager[DatabaseManager]
        Telemetry[Telemetry / Prometheus]
        SQLite[(SQLite DB)]
        Cloud[(Supabase Cloud)]
    end

    %% Interactions
    Browser <--> StreamlitRuntime
    StreamlitRuntime --> ViewModel
    ViewModel --> Renderer
    Renderer --> Components

    ViewModel --> Director
    Director --> Flows
    Director --> Steps
    Steps --> Context

    Steps --> Models
    Flows --> Algo

    Context --> Ports
    SQLiteRepo -.implements.-> Ports
    SupabaseRepo -.implements.-> Ports

    %% Config Switch
    Config[GameConfig] -->|USE_SQLITE| ViewModel
    ViewModel -->|True| SQLiteRepo
    ViewModel -->|False| SupabaseRepo

    SQLiteRepo --> DBManager
    DBManager --> SQLite
    SupabaseRepo --> Cloud

    SQLiteRepo -.-> Telemetry
```

### Gameflow Engine
To visualize this specifically as a Workflow Engine, we can draw it to highlight the "Pipeline" nature of your design.
```mermaid
graph TD
    subgraph "Workflow Definition (The Blueprint)"
        Flow[GameFlow] -->|Builds| Queue[(Step Queue)]
        style Flow fill:#f9f,stroke:#333,stroke-width:2px
    end

    subgraph "Workflow Engine (The Machine)"
        Director[GameDirector]
        Context[GameContext]

        Director -->|Reads| Queue
        Director -->|Injects| Context
        Director -->|Executes| CurrentStep
    end

    subgraph "Workflow Steps (The Units of Work)"
        Step1[TextStep]
        Step2[QuestionLoopStep]
        Step3[SummaryStep]

        Queue -.-> Step1
        Step1 --> Step2
        Step2 --> Step3
    end

    subgraph "External World"
        UI[Streamlit UI] -->|Action: 'Next'| Director
        Director -->|UI Model| UI
    end

    %% Styling to match your "Engine" vibe
    style Director fill:#4CAF50,stroke:#333,stroke-width:4px,color:white
    style Context fill:#673AB7,stroke:#333,stroke-width:2px,color:white
    style Queue fill:#FF9800,stroke:#333,stroke-width:2px
```

Here are the 4 Mermaid diagrams corresponding to the dimensions we discussed. You can copy these directly into your documentation or a Mermaid live editor.

### 1. The Structural View (The Lego Blocks)
**Focus:** Composition. This shows how a "Flow" is just a container for a list of "Steps", and how specific implementations inherit from the base classes.

```mermaid
classDiagram
    %% The Abstract Blocks
    class GameFlow {
        +build_steps() List~GameStep~
    }
    class GameStep {
        +enter(context)
        +handle_action(action, context)
    }

    %% The Concrete Implementations (The Legos)
    class DailySprintFlow
    class CategorySprintFlow

    class TextStep
    class QuestionLoopStep
    class SummaryStep

    %% Relationships
    GameFlow <|-- DailySprintFlow : Inherits
    GameFlow <|-- CategorySprintFlow : Inherits

    GameStep <|-- TextStep : Inherits
    GameStep <|-- QuestionLoopStep : Inherits
    GameStep <|-- SummaryStep : Inherits

    %% Composition (The Key Insight)
    DailySprintFlow *-- TextStep : Contains
    DailySprintFlow *-- QuestionLoopStep : Contains
    DailySprintFlow *-- SummaryStep : Contains

    note for DailySprintFlow "A Flow is just a\nlist of Steps."
```

---

### 2. The Temporal View (The Timeline)
**Focus:** The separation between **Building** the machine and **Running** the machine.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant VM as GameViewModel
    participant Factory as FlowFactory
    participant Director as GameDirector
    participant Queue as StepQueue

    rect rgb(240, 248, 255)
        note right of User: PHASE 1: BUILD TIME (Setup)
        User->>VM: Select "Daily Sprint"
        VM->>Factory: Create DailySprintFlow
        Factory->>Factory: Instantiate Steps [Text, Quiz, Summary]
        Factory-->>Director: Return List of Steps
        Director->>Queue: Load Steps into Queue
    end

    rect rgb(255, 245, 238)
        note right of User: PHASE 2: RUN TIME (Execution)
        Director->>Queue: Pop First Step (TextStep)
        Director->>User: Render UI (Intro)
        User->>Director: Click "Next"
        Director->>Queue: Pop Next Step (QuestionLoopStep)
        Director->>User: Render UI (Question 1)
    end
```

---

### 3. The Data View (The State Flow)
**Focus:** How the `GameContext` (The Backpack) travels through the system and gets modified.

```mermaid
graph LR
    subgraph "The Traveler (GameContext)"
        Context[Context Object<br/>User: 123<br/>Score: 0]
    end

    subgraph "Step 1: Intro"
        TextStep[TextStep]
        TextStep -->|Reads Name| Context
    end

    subgraph "Step 2: The Quiz"
        QuizStep[QuestionLoopStep]
        Context -->|Injects| QuizStep
        QuizStep -->|Updates Score +10| ContextModified[Context Object<br/>User: 123<br/>Score: 10]
    end

    subgraph "Step 3: Results"
        SummaryStep[SummaryStep]
        ContextModified -->|Injects| SummaryStep
        SummaryStep -->|Reads Final Score| DB[(Database)]
    end

    style Context fill:#e1f5fe,stroke:#01579b
    style ContextModified fill:#fff9c4,stroke:#fbc02d
    style DB fill:#eee,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
```

---

### 4. The Control View (The Game Loop)
**Focus:** The logic cycle of the `GameDirector`. This is the "Engine" part.

```mermaid
flowchart TD
    Start([User Action]) --> Input[ViewModel receives Action]
    Input --> Director{Director: handle_action}

    Director -->|Pass to Step| CurrentStep[Active Step Logic]

    CurrentStep --> CheckResult{Is Step Done?}

    CheckResult -- No --> UpdateUI[Update UI Model]

    CheckResult -- Yes --> PopQueue[/Pop Next Step from Queue/]
    PopQueue --> IsQueueEmpty{Is Queue Empty?}

    IsQueueEmpty -- Yes --> Finish([Game Over / Exit])
    IsQueueEmpty -- No --> NewStep[Initialize New Step]
    NewStep --> UpdateUI

    UpdateUI --> Render[[Render to Streamlit]]
    Render --> Start

    style Start fill:#4CAF50,color:white
    style Director fill:#2196F3,color:white
    style CheckResult fill:#FF9800,color:white
    style Render fill:#9C27B0,color:white
```

---

## 2. Component Interaction Patterns

### 2.1. The Passive View Pattern
Streamlit reruns the entire script on every interaction. To prevent logic from resetting or becoming "spaghetti code," we use the **Passive View** pattern.
*   **The Renderer (`src/quiz/presentation/renderer.py`)** is "dumb." It contains no logic. It accepts a `UIModel` (DTO) and simply draws widgets.
*   **The Director (`src/game/director.py`)** calculates the state.
*   **Benefit:** We can unit test the game logic without spinning up a browser.

### 2.2. The State Machine (Game Director)
The application behaves as a finite state machine managed by the `GameDirector`.
*   **Flows:** Factories that define a sequence of states (e.g., `DailySprintFlow` creates `[QuestionLoopStep, SummaryStep]`).
*   **Steps:** Individual states that handle user input (`handle_action`) and define output (`get_ui_model`).
*   **Queue:** The Director manages a queue of steps. When a step returns `"NEXT"`, the Director pops the next step from the queue.

### 2.3. Repository Pattern (Ports & Adapters)
The Domain layer defines *what* it needs (`IQuizRepository`), but not *how* to get it.
*   **Port:** `src/quiz/domain/ports.py`
*   **Adapter:** `src/quiz/adapters/sqlite_repository.py`
*   **Benefit:** Allows swapping SQLite for PostgreSQL or a Mock for testing without changing a single line of the Game Engine.

### 2.4. The Demo Mode Pattern (Multi-Tenancy Lite)
To support sales demos without polluting production data or requiring complex auth:
*   **Trigger:** URL Parameter `?demo=slug` (e.g., `?demo=tesla`).
*   **Isolation:** The `GameViewModel` generates a random UUID for the session, ensuring multiple prospects don't overwrite each other's answers.
*   **Tagging:** The `UserProfile` is tagged with metadata `{"type": "demo", "prospect": "tesla"}` for analytics.
*   **Branding:** The `GameContext` carries the prospect slug, allowing the `Renderer` to dynamically inject custom logos into the UI.
*   **Content:** A specialized `DemoFlow` bypasses the spaced repetition algorithm to serve a fixed, curated list of questions defined in `GameConfig`.
---

## 3. Technology Stack Decisions & Rationale

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | **Python 3.12+** | Leverages modern typing features (`type | None`, `ParamSpec`) for strict static analysis and performance improvements. |
| **Frontend** | **Streamlit** | Enables rapid development of data-heavy UI. We mitigate its "rerun" limitations using the State Machine architecture. |
| **UI Components** | **HTML/JS/CSS** | Custom `st.components.v2` are used for the Mobile Header and Dashboard to bypass Streamlit's styling limitations and provide a native-app feel. |
| **Database (Dev)** | **SQLite** | Enables offline development and rapid iteration. "Force Seed" mode ensures content updates are visible immediately. |
| **Database (Prod)** | **Supabase (PostgreSQL)** | Provides scalable, cloud-based persistence. Uses `UPSERT` logic to allow safe content patching without downtime. |
| **Observability** | **Prometheus & OpenTelemetry** | "Commercial Grade" requirement. Provides real-time metrics (latency, error rates) and distributed tracing capabilities via `src/shared/telemetry.py`. |
| **Quality Assurance** | **Ruff, Mypy, Pytest** | Strict linting and static type checking ensure the codebase remains maintainable and bug-free as it scales. |

---

## 4. Integration Points

### 4.1. Internal Integration (Persistence)
*   **SQLite File:** The app integrates with the local file system at `data/quiz.db`.
*   **Migration System:** The `DatabaseManager` performs schema checks on startup (`_init_schema`, `_migrate_schema`) to ensure the DB structure matches the code version.

### 4.2. External Integration (Observability)
*   **Prometheus Scraper:** The app exposes metrics (via `prometheus-client`). In a production environment, a Prometheus server would scrape these metrics.
*   **Sentry (Configured):** The `pyproject.toml` includes `sentry-sdk`, indicating integration with Sentry for error tracking and crash reporting.

### 4.3. Future Integration (Authentication)
*   **Current State:** Hardcoded to "User1".
*   **Integration Point:** The `GameContext` initialization in `GameViewModel` is the injection point for an external Identity Provider (OAuth2/OIDC).

---

## 5. Data Flow Diagrams

### 5.1. Rendering Flow (Read Path)
How the system decides what to show the user after a reload.

```mermaid
sequenceDiagram
    participant User
    participant Streamlit
    participant ViewModel
    participant Director
    participant Step
    participant Renderer

    User->>Streamlit: Opens App (?demo=tesla)
    Streamlit->>ViewModel: Initialize (Detect Demo)
    ViewModel->>Director: get_ui_model()
    Director->>Step: get_ui_model()

    Step->>Step: Check Context.is_demo
    Step-->>Director: UIModel (branding_logo="tesla.png")

    Director-->>ViewModel: UIModel
    ViewModel->>Renderer: render(UIModel)

    Renderer->>Renderer: Inject Logo into Payload
    Renderer->>Streamlit: Draw Widgets (with Custom Logo)
    Streamlit-->>User: Display Page
```

### 5.2. Action Flow (Write Path)
How the system processes a user answer.

```mermaid
sequenceDiagram
    participant User
    participant Streamlit
    participant ViewModel
    participant Director
    participant Step
    participant Context
    participant Repo

    User->>Streamlit: Clicks "Option A"
    Streamlit->>ViewModel: Callback("SUBMIT_ANSWER", "A")
    ViewModel->>Director: handle_action("SUBMIT_ANSWER", "A")
    Director->>Step: handle_action(...)

    Step->>Step: Check Logic (Correct/Wrong)
    Step->>Context: Update Score
    Step->>Repo: save_attempt(user, question, result)
    Repo-->>Step: Success

    Step-->>Director: Return None (Stay on Step)
    Director-->>ViewModel: State Updated
    ViewModel->>Streamlit: st.rerun()
```
