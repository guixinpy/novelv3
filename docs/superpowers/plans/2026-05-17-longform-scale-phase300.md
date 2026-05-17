# Longform Scale Phase 300 - Avoid Worker Active Task Lookup

## Goal

Prevent active task recovery logic from adding per-chapter overhead inside continuous writing workers.

## Finding

After active `task_id` recovery was added, `WritingStateService.state()` looked up active background tasks by default. `build_generate_chapter_work()` calls `state()` before every generated chapter, so a 1000 chapter run could perform 1000 extra active task lookup queries.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_status_check_skips_active_task_lookup -q
```

Observed failure:

```text
active_task_lookups contained 4 background task lookup queries
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py::test_generate_chapter_work_status_check_skips_active_task_lookup backend\tests\test_writing.py::test_writing_state_endpoint_returns_active_task_id -q
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q
```

Observed result:

```text
2 passed
35 passed
```

## Change

- `WritingStateService.state()` still includes active `task_id` by default for API reads.
- Internal `run_chapter()` and worker status checks skip active task id lookup unless explicitly requested.
- `build_generate_chapter_work()` calls the lightweight state path.

## Verification

Full phase gate passed:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` - 691 passed
- `npm run build` - passed
- `npm run test:unit -- --run` - 440 passed
- `git diff --check` - passed
- DeepSeek key scan - `NO_MATCH`
