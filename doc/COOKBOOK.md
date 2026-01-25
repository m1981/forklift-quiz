# 🍳 Developer Cookbook

## How to add a new Scenario?
1.  Create a new class in `src/game/flows.py` inheriting from `GameFlow`.
2.  Implement `build_steps(context)`.
3.  Return a list of `TextStep` or `QuestionLoopStep`.
4.  Add a button in `app.py` to trigger `vm.director.start_flow(NewFlow())`.

## How to add a new Screen Type?
1.  Create a class in `src/game/steps.py` inheriting from `GameStep`.
2.  Define a `Payload` dataclass for the data it needs.
3.  Implement `get_ui_model` to return `UIModel(type="MY_NEW_TYPE", payload=...)`.
4.  Update `src/quiz/presentation/renderer.py` to handle `"MY_NEW_TYPE"`.
