To understand the **User Flows** completely—from the moment a user clicks a button to how the application decides which screen to show next—you should examine these **4 specific files** in this order.

They represent the **Definition**, **Execution**, **Logic**, and **Trigger** of your flows.

### 1. The Blueprint (Flow Definition)
**File:** `src/game/flows.py`
*   **Why:** This is the "Map". It defines the linear sequence of screens for a specific scenario.
*   **What to look for:**
    *   The `build_steps` method in `DailySprintFlow`.
    *   You will see the high-level structure: `TextStep` (Intro) $\rightarrow$ `QuestionLoopStep` (Game) $\rightarrow$ `SummaryStep` (Results).
    *   It also contains the logic for **Conditional Flows** (e.g., checking `is_bonus` to decide if the user gets 5 or 15 questions).

### 2. The Logic (Branching & Micro-Flows)
**File:** `src/game/steps.py`
*   **Why:** This handles the internal state machine of a specific screen and **Dynamic Branching**.
*   **What to look for:**
    *   **`QuestionLoopStep.handle_action`**: This defines the "Micro-Flow" of the quiz: *Question $\rightarrow$ Submit $\rightarrow$ Feedback $\rightarrow$ Next*.
    *   **`SummaryStep.handle_action`**: This is where the **Dynamic Branching** happens (as seen in your Sequence Diagram). Look specifically at the `REVIEW_MISTAKES` block where it returns a *new instance* of `QuestionLoopStep` instead of just a string signal.

### 3. The Engine (State Transitions)
**File:** `src/game/director.py`
*   **Why:** This is the "Traffic Controller". It executes the flow defined in #1 and handles the branching returned by #2.
*   **What to look for:**
    *   **`_advance()`**: How it pops the next step from the queue.
    *   **`handle_action()`**: Specifically the `elif isinstance(result, GameStep):` block. This is the exact line of code that enables the "Review Mistakes" feature to inject a new loop into the middle of an existing session.

### 4. The Trigger (Entry Point)
**File:** `src/quiz/presentation/viewmodel.py`
*   **Why:** This connects the UI to the Engine. It shows how a user click translates into a Flow start.
*   **What to look for:**
    *   `start_daily_sprint()`: Calls `director.start_flow(DailySprintFlow())`.
    *   `_check_auto_start()`: Shows how the app decides to force the `OnboardingFlow` for new users.

### Summary of the "Review Mistakes" Flow
To trace the specific complex flow you diagrammed:

1.  **Start:** `viewmodel.py` (User clicks button)
2.  **Setup:** `flows.py` (Defines the initial list of steps)
3.  **Execution:** `director.py` (Iterates through steps)
4.  **Branching:** `steps.py` (`SummaryStep` creates a new `QuestionLoopStep` with error IDs)
5.  **Injection:** `director.py` (Inserts that new step into `self._queue`)




Based on the four files provided (`viewmodel.py`, `flows.py`, `director.py`, `steps.py`), here are the detailed Mermaid diagrams capturing the architecture and user flows.

### 1. High-Level State Machine (User Navigation)
This diagram represents the **GameDirector's** state transitions as controlled by `viewmodel.py` and `flows.py`. It shows how the app moves from the Dashboard into specific flows and how the "Review Mistakes" branch loops back.

```mermaid
stateDiagram-v2
    [*] --> Dashboard : App Start / Refresh

    state "Dashboard - Empty State" as Dashboard {
        [*] --> Idle
        Idle --> CheckAutoStart : viewmodel._check_auto_start
        CheckAutoStart --> OnboardingFlow : if not has_completed_onboarding
        CheckAutoStart --> Idle : else
    }

    Dashboard --> DailySprintFlow : User clicks Start Sprint
    Dashboard --> OnboardingFlow : User clicks Start Onboarding

    state DailySprintFlow {
        [*] --> IntroStep : flows.DailySprintFlow.build_steps
        IntroStep --> QuestionLoop : Action NEXT
        
        state QuestionLoop {
            [*] --> AwaitingAnswer
            AwaitingAnswer --> Feedback : Action SUBMIT_ANSWER
            Feedback --> AwaitingAnswer : Action NEXT_QUESTION
            Feedback --> [*] : No more questions
        }

        QuestionLoop --> SummaryStep
        
        state SummaryStep {
            [*] --> ShowResults
            ShowResults --> ReviewBranch : Action REVIEW_MISTAKES
            ShowResults --> Finish : Action FINISH
        }

        state ReviewBranch {
            [*] --> ReviewLoop
            note right of ReviewLoop
                Created dynamically in 
                steps.SummaryStep
            end note
            ReviewLoop --> SummaryStep : Loop Finished
        }
    }

    DailySprintFlow --> Dashboard : Flow Complete
    OnboardingFlow --> Dashboard : Flow Complete
```

### 2. Sequence Diagram: The "Review Mistakes" Dynamic Branching
This diagram focuses specifically on the logic found in `steps.py` (SummaryStep) and `director.py` (handle_action), illustrating how a new step is injected into the running queue.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant VM as GameViewModel
    participant Director as GameDirector
    participant Summary as SummaryStep
    participant Context as GameContext

    Note over User, VM: User is on the Summary Screen
    User->>VM: Click Popraw Błędy
    VM->>Director: handle_action REVIEW_MISTAKES
    
    Director->>Summary: handle_action REVIEW_MISTAKES, context
    
    activate Summary
    Summary->>Context: context.data.get errors
    Context-->>Summary: Returns ID_1, ID_5
    
    Summary->>Context: repo.get_questions_by_ids ID_1, ID_5
    Context-->>Summary: Returns QuestionObj1, QuestionObj5
    
    Summary->>Context: Clear errors in data
    
    Note right of Summary: CRITICAL - Creating new Step instance
    create participant NewLoop as QuestionLoopStep - New Instance
    Summary->>NewLoop: init with QuestionObj1, QuestionObj5
    
    Summary-->>Director: Returns NewLoop - GameStep Instance
    deactivate Summary

    Note right of Director: Logic from director.py lines 58-61
    Director->>Director: isinstance result, GameStep is True
    Director->>Director: _queue.insert 0, result
    Director->>Director: _advance
    
    Director->>NewLoop: enter context
    Director-->>VM: Flow Updated
    VM-->>User: Renders Question View - Review Mode
```

### 3. Sequence Diagram: Standard Gameplay Loop
This captures the interaction in `QuestionLoopStep` (`steps.py`) and how it communicates with the `Director` and `Context`.

```mermaid
sequenceDiagram
    actor User
    participant VM as GameViewModel
    participant Director as GameDirector
    participant QLoop as QuestionLoopStep
    participant Context as GameContext

    Note over User, QLoop: Inside DailySprintFlow - QuestionLoopStep

    User->>VM: Select Option A
    VM->>Director: handle_action SUBMIT_ANSWER, A
    Director->>QLoop: handle_action SUBMIT_ANSWER, A
    
    activate QLoop
    QLoop->>QLoop: Check correctness
    
    alt Answer is Correct
        QLoop->>Context: data score += 1
        QLoop->>Context: repo.save_attempt correct=True
    else Answer is Wrong
        QLoop->>Context: data errors append id
        QLoop->>Context: repo.save_attempt correct=False
    end
    
    QLoop->>QLoop: Set feedback_mode = True
    QLoop-->>Director: Return None - Stay on Step
    deactivate QLoop
    
    Director-->>VM: UI Model Type FEEDBACK
    VM-->>User: Show Green/Red Feedback

    User->>VM: Click Next Question
    VM->>Director: handle_action NEXT_QUESTION
    Director->>QLoop: handle_action NEXT_QUESTION
    
    activate QLoop
    QLoop->>QLoop: index += 1
    
    alt Has More Questions
        QLoop->>QLoop: feedback_mode = False
        QLoop-->>Director: Return None - Stay
        Director-->>VM: UI Model Type QUESTION
    else No More Questions
        QLoop-->>Director: Return NEXT
        Director->>Director: _advance - Pops SummaryStep
    end
    deactivate QLoop
```

### Key Architectural Patterns Highlighted
1.  **The Trigger (`viewmodel.py`):** The ViewModel is the only entry point for the UI. It decides whether to start a flow (`start_daily_sprint`) or pass an action to the engine.
2.  **The Engine (`director.py`):** It is agnostic of *what* step is running. It just handles the queue. The `isinstance(result, GameStep)` check is the key enabler for dynamic flows.
3.  **The Logic (`steps.py`):** The steps are self-contained. `QuestionLoopStep` manages its own index and feedback state. `SummaryStep` has the intelligence to query the Context and generate a new Step object.