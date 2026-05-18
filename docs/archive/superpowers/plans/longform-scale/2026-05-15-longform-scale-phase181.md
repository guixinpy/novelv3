# Phase 181 - Bound Default Plotline Milestone Windows

## Problem

After defaulting evolution plan reads to window mode, the nested plotline milestone
window still defaulted to 500 items per plotline. A default request with many
plotlines could still return tens of thousands of nested milestones.

## Change

- Added a regression test with a 1000-node plotline and no explicit query params.
- Reduced the default `milestone_limit` from 500 to 80, matching the narrative
  storyline view's bounded window.
- Kept the explicit maximum at 500 so graph-oriented callers can still request a
  wider milestone window deliberately.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py::test_evolution_plan_default_mode_bounds_plotline_milestones -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py::test_evolution_plan_default_mode_bounds_plotline_milestones -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Default narrative plan reads now bound both top-level arrays and nested plotline
milestones, while preserving explicit larger windows for graph mode.
