# Phase 180 - Default Evolution Plan to Window Mode

## Problem

`GET /athena/evolution/plan` defaulted to `mode=full`, so any caller that forgot
to pass window parameters could pull the full outline and storyline JSON. On a
thousand-chapter project this means returning every chapter plan, plotline, and
foreshadowing item in one response.

## Change

- Added a regression test proving the default request returns a bounded window and
  does not select full outline/storyline JSON columns.
- Changed the default `mode` query parameter from `full` to `window`.
- Preserved explicit `mode=full` for compatibility and diagnostics.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py::test_evolution_plan_default_mode_is_windowed_for_longform_safety -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py::test_evolution_plan_default_mode_is_windowed_for_longform_safety -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Narrative plan reads are bounded by default, reducing accidental large responses
for longform projects while keeping full mode opt-in.
