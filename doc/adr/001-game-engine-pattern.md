# ADR 001: Adoption of Game Engine (Director/Step) Pattern

## Status
Accepted

## Context
The initial application used a rigid Finite State Machine (FSM) combined with a Service layer. 
Adding new scenarios (like Onboarding or Bonus Rounds) required modifying the core FSM and adding complex `if/else` logic to the Service.

## Decision
We refactored the application to use a **Director/Flow/Step** pattern.
*   **Flows** define the sequence of screens.
*   **Steps** encapsulate logic for a single screen.
*   **Director** executes the steps in order.

## Consequences
*   **Positive:** Adding a new flow (e.g., "Sudden Death Mode") requires zero changes to existing code.
*   **Positive:** UI logic is decoupled from Business logic via `UIModel` DTOs.
*   **Negative:** Slightly higher complexity for simple linear flows.