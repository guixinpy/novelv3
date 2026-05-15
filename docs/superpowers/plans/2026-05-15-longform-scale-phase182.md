# Phase 182 - Bound Default Plotline Windows

## Problem

The default evolution plan window still returned up to 100 plotlines. Because each
plotline can carry nested milestones, a no-parameter plan request could still be
large even after the nested milestone limit was reduced.

## Change

- Tightened the default `plotline_limit` from 100 to 20.
- Preserved the explicit maximum of 500 for deliberate graph-oriented requests.
- Updated the default longform safety regression to require `plotlines_has_more`
  when more plotlines are available.

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

Default narrative plan reads now match the frontend's bounded storyline window,
while explicit callers can still request wider graph windows.
