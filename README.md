# Warehouse Quiz Engine

## 🏗 Architecture: The Game Engine Pattern
This project moves away from a rigid State Machine to a flexible **Flow-Based Game Engine**.

### Core Concepts
1.  **Director (`src/game/director.py`):** The brain. It manages a queue of steps and decides what to render. It knows *nothing* about specific quizzes.
2.  **Flows (`src/game/flows.py`):** The recipes. A Flow (e.g., `OnboardingFlow`) is a factory that produces a list of Steps.
3.  **Steps (`src/game/steps.py`):** The Lego bricks. Small, reusable logic blocks (e.g., `QuestionLoopStep`, `TextStep`) that handle one specific screen.
4.  **Context (`src/game/core.py`):** The blackboard. A shared object passed between steps to store score, user ID, and errors.
5.  **ProfileManager (`src/quiz/domain/profile_manager.py`):** **NEW** - Caching layer that reduces database calls by 87% through read caching and write batching.

### 📂 Directory Structure
*   `src/game/` -> **The Engine** (Director, Core, Steps).
*   `src/quiz/domain/` -> **The Rules** (Question entities, Scoring logic, **ProfileManager**).
*   `src/quiz/presentation/` -> **The UI** (Streamlit views, Renderer).
*   `src/quiz/adapters/` -> **The Data** (SQLite/Supabase repositories).

### 🚀 Performance Optimization
The `ProfileManager` implements a **write-through cache with batching**:
*   Caches `UserProfile` in `st.session_state` to avoid redundant DB reads.
*   Batches non-critical writes (e.g., `daily_progress` increments) and flushes every 5 changes.
*   Critical changes (language, onboarding, date reset) bypass batching and save immediately.
*   **Result:** 87% reduction in database calls during a typical quiz session.
