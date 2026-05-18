# Phase 185 - Cover Narrative Plan Window In Longform Smoke

## Problem

The evolution-plan API already defaults to bounded window mode, but the
million-word smoke path did not exercise that same backend code path. That left
a regression gap: smoke could pass while the narrative plan still loaded or
returned large JSON arrays outside the API tests.

## Change

- Moved the evolution-plan window query into `app.core.narrative_plan_window`.
- Kept the API behavior unchanged by calling the shared helper from
  `/evolution/plan`.
- Seeded synthetic longform smoke projects with chapters, outline plotlines,
  storyline plotlines, milestones, and foreshadowing.
- Added a compact `narrative_plan` section to smoke output, proving bounded
  chapter, plotline, milestone, and foreshadowing windows.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_bounded_narrative_plan_window -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_bounded_narrative_plan_window -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_memory_retrieval_and_resume_progress backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_stage_timings backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_bounded_narrative_plan_window backend\tests\test_athena_evolution_plan.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`591 passed`)
- GREEN: `npm run test:unit` from `frontend` (`402 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

The million-word smoke now reports bounded narrative plan coverage:
100 of 1000 chapters, 20 of 60 storylines, 80 of 1000 milestones, and 100 of
300 foreshadowing entries. The measured `narrative_plan_window` stage took 8ms
in the 1000-chapter smoke run.
