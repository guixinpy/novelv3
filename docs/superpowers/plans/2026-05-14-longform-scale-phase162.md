# Phase 162 - Window storyline milestones

## Goal

Add backend, client, and store support for windowing milestones inside returned storyline plotlines.

## Why

Plotline windows limit the number of plotline objects, but a single main plotline in a thousand-chapter novel can still contain hundreds or thousands of milestone nodes. The API needs a second-level milestone window so storylines can be loaded without shipping every node at once.

## TDD

RED 1:

- Added a backend test with one plotline containing 1000 milestones.
- Requested `mode=window&plotline_limit=1&milestone_offset=200&milestone_limit=3`.
- It failed because the API returned all 1000 milestones.

RED 2:

- Extended the frontend API client test to require `milestone_offset` and `milestone_limit` serialization.
- It failed because those params were dropped.

RED 3:

- Added a store regression test for the first `loadEvolutionPlan` after project activation.
- It failed because the request sequence was incremented before `ensureProject`, and `reset()` invalidated the first response.

GREEN:

- Added `milestone_offset` and `milestone_limit` query params to the backend endpoint.
- Windowed storyline plotlines now include `milestones`, `milestones_total`, `milestones_offset`, `milestones_limit`, and `milestones_has_more`.
- Added milestone query serialization and typing in the frontend API layer.
- Included milestone params in the Athena store evolution-plan cache key.
- Moved project activation before the evolution-plan request sequence guard so the first plan load writes state correctly.

## Verification

- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_athena_evolution_plan.py -q` -> 2 passed
- `npm run test:unit -- client.athenaEvolutionPlan` -> 1 passed
- `npm run test:unit -- athena.scope` -> 13 passed
- `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` -> 579 passed
- `npm run test:unit` -> 61 files / 390 tests passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed

## Note

Running backend tests with system `python` failed because system Python does not have the project Alembic dependency installed. The project virtual environment is the correct backend test runner on this machine.
