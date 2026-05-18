# Phase 199 - Cover Dialog Planning Context In Longform Smoke

## Problem

The million-word smoke test covered longform memory, retrieval, narrative-plan
windows, and background-task progress, but it did not exercise Athena dialog's
narrative-planning context. That path is important because users repeatedly ask
Athena global planning questions during long-form writing.

## Change

- Added smoke assertions for a bounded Athena dialog planning context summary.
- Added a `dialog_planning_context` report section with:
  - availability.
  - context kind.
  - content character count.
  - token estimate.
  - truncation flag.
- Added a separate `dialog_planning_context` timing stage.
- Stored the compact dialog-planning context in the completed smoke task result.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q` (`39 passed`)
- GREEN: `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
  - `dialog_planning_context`: available, `narrative_planning_summary`, 124 chars, 4 ms.
  - total elapsed: 8723 ms.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`601 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`407 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

The longform smoke now covers Athena's global planning dialog context. Future
changes that accidentally let this path expand into a large prompt or slow query
will show up in the standard million-word smoke report.
