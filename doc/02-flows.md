# System Architecture & Design Documentation

## Executive Summary
This document outlines the technical specifications for the **Warehouse Quiz App**, a commercial-grade adaptive learning platform built on **Streamlit**.

Unlike typical Streamlit prototypes, this application utilizes a strict **Hexagonal Architecture (Ports & Adapters)** to decouple business logic from the user interface and database. Key features include:
*   **Adaptive Learning:** A "Spaced Repetition" algorithm that prioritizes questions based on user mastery and time decay.
*   **State Machine Engine:** A robust Director/Flow pattern that manages complex user sessions (Onboarding, Sprints, Reviews) without relying on fragile script execution.
*   **Mobile-First UI:** Custom Shadow DOM components injected into Streamlit to provide a native-app experience on mobile devices.

---

## Project Structure: What is Where?

The codebase is organized by **Architectural Layer** rather than technical function.

### 1. Domain Layer (The "Brain")
*Located in:* `src/quiz/domain/`
*   **Purpose:** Contains pure business logic and entities. Zero dependencies on the UI or Database.
*   **Key Files:**
    *   `models.py`: Defines core entities (`Question`, `UserProfile`).
    *   `ports.py`: Defines interfaces (`IQuizRepository`) that the infrastructure must implement.
    *   `spaced_repetition.py`: The algorithm deciding which questions to show next.

### 2. Application Layer (The "Engine")
*Located in:* `src/game/`
*   **Purpose:** Manages the user session state and screen transitions.
*   **Key Files:**
    *   `director.py`: The central state machine processor.
    *   `flows.py`: Factories that build scenarios (e.g., `DailySprintFlow`, `OnboardingFlow`).
    *   `steps/`: Individual screen logic (e.g., `QuestionLoopStep`, `DashboardStep`).

### 3. Infrastructure Layer (The "Plumbing")
*Located in:* `src/quiz/adapters/`
*   **Purpose:** Implements the Domain interfaces to talk to the outside world (Database).
*   **Key Files:**
    *   `sqlite_repository.py`: The concrete implementation of the database storage.
    *   `db_manager.py`: Handles SQLite connections and migrations in a pickle-safe way.

### 4. Presentation Layer (The "Face")
*Located in:* `src/quiz/presentation/` and `src/components/`
*   **Purpose:** Handles rendering. It is a "Passive View" that only displays what the Engine tells it to.
*   **Key Files:**
    *   `renderer.py`: Maps Engine DTOs to Streamlit widgets.
    *   `src/components/mobile/`: Contains the custom HTML/CSS/JS for the mobile-specific UI (Header, Options, Dashboard Grid).

---
*(Diagrams follow below)*

### Task Flow 1: Complete Daily Sprint
This represents the primary "Happy Path" for a returning user engaging with the Spaced Repetition algorithm.
```mermaid
flowchart TD
    Start([User on Dashboard]) --> ClickSprint[Click 'Start Daily Sprint' Button]

    ClickSprint --> SystemAlgo[System: Selects 15 Questions<br/>Spaced Repetition Logic]
    SystemAlgo --> LoadQ[Load Question Screen]

    LoadQ --> ReadQ[User Reads Question]
    ReadQ --> SelectOpt[Select Answer Option]

    SelectOpt --> SystemCheck{Is Correct?}
    SystemCheck -->|Yes| UpdateStreak[System: Increment Streak]
    SystemCheck -->|No| LogError[System: Log Error ID]

    UpdateStreak --> ShowFeed[Show Feedback Screen]
    LogError --> ShowFeed

    ShowFeed --> ClickNext[Click 'Dalej' Button]

    ClickNext --> MoreQ{More Questions?}
    MoreQ -->|Yes| LoadQ

    MoreQ -->|No| CalcStats[System: Calculate Score]
    CalcStats --> ShowSum[Show Summary Screen]

    ShowSum --> ClickFinish[Click 'Menu Główne']
    ClickFinish --> End([Task Complete: Return to Dashboard])

    style Start fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    style End fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    style SystemAlgo fill:#fff3e0,stroke:#ffa726
    style UpdateStreak fill:#fff3e0,stroke:#ffa726
    style LogError fill:#ffebee,stroke:#ef5350
    style CalcStats fill:#fff3e0,stroke:#ffa726
```

### Task Flow 2: Review Mistakes
This flow illustrates the specific remediation task triggered when a user fails a quiz. It relies on the logic found in src/game/steps/summary.py.
```mermaid
flowchart TD
    Start([User at Summary Screen]) --> CheckScore{Passed Quiz?}

    CheckScore -->|Yes| Finish([End Task])

    CheckScore -->|No| ViewErrors[User sees 'Negative' Grade]
    ViewErrors --> ClickReview[Click 'Popraw Błędy' Button]

    ClickReview --> FetchErrors[System: Fetch Failed Questions Only]
    FetchErrors --> StartLoop[Start Review Loop]

    StartLoop --> ViewQ[View Previously Failed Question]
    ViewQ --> SelectOpt[Select Correct Option]

    SelectOpt --> ShowFeed[Show Feedback]
    ShowFeed --> ClickNext[Click 'Dalej']

    ClickNext --> MoreErrors{More Errors?}
    MoreErrors -->|Yes| ViewQ

    MoreErrors -->|No| ShowNewSum[Show Updated Summary]
    ShowNewSum --> ClickMenu[Click 'Menu Główne']
    ClickMenu --> End([Task Complete: Return to Dashboard])

    style Start fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    style End fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    style ViewErrors fill:#ffebee,stroke:#ef5350
    style FetchErrors fill:#fff3e0,stroke:#ffa726
    style ClickReview fill:#e3f2fd,stroke:#2196f3
```

### Task Flow 3: First-Time Onboarding
This flow represents the initialization task defined in src/game/flows.py (OnboardingFlow) and triggered by src/quiz/presentation/viewmodel.py.
```mermaid
flowchart TD
    Start([User Opens App]) --> CheckProfile[System: Check User Profile]

    CheckProfile --> IsNew{Is New User?}
    IsNew -->|No| Dashboard([Go to Dashboard])

    IsNew -->|Yes| StartFlow[Start Onboarding Flow]
    StartFlow --> ViewIntro[View 'Witaj w Magazynie' Screen]

    ViewIntro --> ClickNext1[Click 'Dalej']
    ClickNext1 --> ViewTutQ[View Tutorial Question]

    ViewTutQ --> SelectTutOpt[Select Answer]
    SelectTutOpt --> ViewTutFeed[View Feedback & Explanation]

    ViewTutFeed --> ClickNext2[Click 'Dalej']
    ClickNext2 --> ViewOutro[View 'Szkolenie Zakończone' Screen]

    ViewOutro --> MarkComplete[System: Set onboarding_complete = True]
    MarkComplete --> ClickStart[Click 'Rozpocznij Sprint']

    ClickStart --> End([Task Complete: Dashboard Loaded])

    style Start fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    style End fill:#e1f5e1,stroke:#4caf50,stroke-width:3px
    style Dashboard fill:#eeeeee,stroke:#9e9e9e
    style MarkComplete fill:#fff3e0,stroke:#ffa726
    style CheckProfile fill:#fff3e0,stroke:#ffa726
```

```mermaid
graph TD
    %% --- ENTRY POINT ---
    Start([User Opens App]) --> Init{Onboarding<br/>Complete?}

    %% --- ONBOARDING FLOW ---
    Init -->|No| OnboardIntro[Intro Screen<br/>'Witaj w Magazynie']
    OnboardIntro -->|Next| OnboardTut[Tutorial Question<br/>'Szkolenie Wstępne']
    OnboardTut -->|Submit| OnboardOutro[Completion Screen<br/>'Gotowy do pracy']
    OnboardOutro -->|Start| Dashboard

    %% --- DASHBOARD ---
    Init -->|Yes| Dashboard[Dashboard Screen<br/>Hero Stats & Grid]

    %% --- DASHBOARD ACTIONS ---
    Dashboard --> Action{User Choice}
    Action -->|Tap 'Rocket'| DailySprint[Daily Sprint Flow]
    Action -->|Tap Category| CatSprint[Category Flow]

    %% --- GAME LOOP (Shared Logic) ---
    DailySprint --> Q_View
    CatSprint --> Q_View

    Q_View[Question Screen] -->|Select Option| Q_Submit{Submit?}
    Q_Submit -->|Yes| Q_Feedback[Feedback Screen<br/>Correct/Wrong + Explanation]

    Q_Feedback -->|Next| CheckMore{More<br/>Questions?}
    CheckMore -->|Yes| Q_View

    %% Home Button Logic (Global Exit)
    Q_View -.->|Home Icon| Dashboard
    Q_Feedback -.->|Home Icon| Dashboard

    %% --- SUMMARY & REVIEW ---
    CheckMore -->|No| Summary[Summary Screen<br/>Score & Balloons]

    Summary --> SumAction{Action}
    SumAction -->|Main Menu| Dashboard

    %% --- REVIEW MISTAKES PATH ---
    SumAction -->|'Popraw Błędy'<br/>If Errors Exist| ReviewLoop[Review Loop<br/>Failed Questions Only]
    ReviewLoop -->|Finish| Dashboard

    %% --- STYLING ---
    style Start fill:#e1f5e1,stroke:#2e7d32,stroke-width:2px
    style Dashboard fill:#e3f2fd,stroke:#1565c0,stroke-width:2px

    style OnboardIntro fill:#fff3e0
    style OnboardTut fill:#fff3e0
    style OnboardOutro fill:#fff3e0

    style Q_View fill:#ffffff,stroke:#333
    style Q_Feedback fill:#f5f5f5,stroke:#333
    style Summary fill:#e8f5e9,stroke:#2e7d32

    style ReviewLoop fill:#ffebee,stroke:#c62828,stroke-dasharray:5 5

    style Init fill:#fff9c4,stroke:#fbc02d
    style Action fill:#fff9c4,stroke:#fbc02d
    style CheckMore fill:#fff9c4,stroke:#fbc02d
    style SumAction fill:#fff9c4,stroke:#fbc02d
```

### UI Composition Diagram (The "Face")
Audience: Frontend Developers, UI Designers.
Purpose: Because you are "hacking" Streamlit to look like a mobile app, this diagram is crucial. It maps the Visual Elements to the Code Components. It clearly distinguishes between what is standard Streamlit (Python) and what is Custom Component (HTML/JS/CSS).

```mermaid
graph TD
    subgraph Root["Mobile Screen Layout (Streamlit Page)"]

        subgraph Zone1["Zone 1: Navigation & Context"]
            Header["<b>Custom Component: Mobile Header</b><br/>src/components/mobile/header.py<br/><i>(HTML/JS/CSS Shadow DOM)</i>"]
        end

        subgraph Zone2["Zone 2: Content Area"]
            QText["<b>Native Streamlit: Markdown</b><br/>st.markdown(question.text)"]
            QImage["<b>Native Streamlit: Image</b><br/>st.image(path)"]
        end

        subgraph Zone3["Zone 3: Interaction Area"]
            Options["<b>Custom Component: Mobile Option</b><br/>src/components/mobile/option.py<br/><i>(Repeated for A, B, C, D)</i>"]
        end

        subgraph Zone4["Zone 4: Feedback (Conditional)"]
            Expander["<b>Native Streamlit: Expander</b><br/>st.expander('Hint')"]
            NextBtn["<b>Native Streamlit: Button</b><br/>st.button('Dalej')"]
        end

        Zone1 --> Zone2
        Zone2 --> Zone3
        Zone3 --> Zone4
    end

    %% Styling
    style Root fill:#f9f9f9,stroke:#333,stroke-width:2px
    style Zone1 fill:#e3f2fd,stroke:#2196f3
    style Zone2 fill:#fff3e0,stroke:#ff9800
    style Zone3 fill:#e8f5e9,stroke:#4caf50
    style Zone4 fill:#ffebee,stroke:#f44336

    %% Annotations for Tech Stack
    classDef custom fill:#d1c4e9,stroke:#673ab7,color:black
    classDef native fill:#b2dfdb,stroke:#009688,color:black

    class Header,Options custom
    class QText,QImage,Expander,NextBtn native
```

### Data State Transition Diagram (The "Brain")
Audience: Data Scientists, Backend Developers.
Purpose: This diagram explains the Spaced Repetition Logic found in src/quiz/domain/spaced_repetition.py and src/quiz/adapters/sqlite_repository.py. It visualizes the lifecycle of a single Question entity, which is the core value proposition of your a
```mermaid
stateDiagram-v2
    state "Unseen (New)" as New
    state "Learning Phase" as Learning
    state "Review Phase" as Review
    state "Mastered" as Mastered

    [*] --> New

    New --> Learning : First Attempt (Correct or Wrong)

    state Learning {
        [*] --> Streak0
        Streak0 --> Streak1 : Correct Answer
        Streak1 --> Streak0 : Wrong Answer
        Streak1 --> Streak2 : Correct Answer
        Streak2 --> Streak0 : Wrong Answer
    }

    %% Transition based on GameConfig.MASTERY_THRESHOLD (e.g., 3)
    Learning --> Mastered : Streak >= Threshold (3)

    state Mastered {
        [*] --> Dormant

        %% Logic from sqlite_repository: date('now', '-3 days')
        Dormant --> ReviewCandidate : Time Decay (> 3 Days)
        ReviewCandidate --> Dormant : Reviewed Correctly
    }

    %% Regression Logic
    Mastered --> Learning : Reviewed Incorrectly (Streak Reset)

    note right of Mastered
        Questions here are hidden
        from Daily Sprint until
        Time Decay triggers.
    end note
```
