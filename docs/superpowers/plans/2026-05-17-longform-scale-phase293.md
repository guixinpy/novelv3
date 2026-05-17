# Longform Scale Phase 293 - Visible Continuous Writing Progress

## Assumption

Continuous writing over hundreds or thousands of chapters must expose progress during the task, not only after task completion.

## Risk

The frontend polls background tasks with `compact=true`. Compact responses previously dropped `result`, so range progress was invisible and Hermes could keep showing the initial writing pointer for a long-running task.

## Change

1. Compact background task responses now include only compact `result.progress` when present.
2. Project store polling applies `progress.next_chapter_index` to the local writing state while the task is still running.
3. Terminal task handling still refreshes authoritative project targets from the backend.

## Verification

- Red:
  - `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_background.py::test_get_background_task_compact_includes_range_progress -q` failed because compact `result` was `null`.
  - `npm run test:unit -- --run src/stores/project.workspace.test.ts` failed because `writingState.current_chapter` stayed at the initial chapter.
- Green:
  - `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_background.py::test_get_background_task_compact_includes_range_progress backend\\tests\\test_writing.py -q` passed with 23 tests.
  - `npm run test:unit -- --run src/stores/project.workspace.test.ts` passed with 29 tests.
- Full verification will run before commit.
