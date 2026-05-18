# Longform Scale Phase 294 - Deduplicate Active Writing Range Tasks

## Assumption

Users may click start/resume while a long continuous writing task is already running.

## Risk

The old deduplication checked only `payload.chapter_index`. Once a range task had advanced from chapter 1 to chapter 5, another start could create a duplicate task from chapter 5 to the target, causing overlapping generation and corrupted progress.

## Change

1. Active `generate_chapter` lookup now considers all active project tasks.
2. A task is reused when the requested chapter equals its single `chapter_index` or falls inside its `chapter_range`.
3. Retry tasks keep their exact chapter deduplication behavior.

## Verification

- Red: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_writing.py::test_writing_start_reuses_active_range_task_covering_current_chapter -q` failed because a duplicate task was created.
- Green: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_writing.py -q` passed with 23 tests.
- Full verification will run before commit.
