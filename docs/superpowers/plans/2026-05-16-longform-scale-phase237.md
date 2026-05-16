# Phase 237: Bound Athena Optimization Rules

## Goal

Prevent Athena optimization from returning an unbounded list of learned prompt rules as a project accumulates many revisions and self-optimization events.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_self_optimization.py::test_athena_optimization_endpoint_returns_bounded_rule_window -q`
  - Failed because `/athena/optimization` returned all 130 learned rules and no pagination metadata.
- `npm run test:unit -- --run src/api/client.worldModel.test.ts`
  - Failed because `getAthenaOptimization()` ignored `rules_offset` and `rules_limit`.

## GREEN

- Added `rules_offset` and `rules_limit` query parameters to `/athena/optimization`.
- Added `rules_total`, `rules_offset`, `rules_limit`, and `rules_has_more` to the response.
- Added frontend `AthenaOptimizationQuery` and query serialization.

## Verification

- Targeted backend and frontend tests pass after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.
