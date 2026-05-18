# Phase 190 - Route Outline And Storyline Reads Through Plan Windows

## Problem

Hermes no longer eagerly hydrates optional outline/storyline data, but explicit
`loadOutline()` and `loadStoryline()` still used the deprecated full JSON
endpoints. A long project could still pull thousand-chapter outline/storyline
payloads when a refresh target or panel asked for those resources.

## Change

- Added API client regression tests for `getOutline()` and `getStoryline()`.
- Routed both methods through `/athena/evolution/plan?mode=window`.
- Returned only the requested `outline` or `storyline` sub-tree to preserve the
  project store call shape.
- Updated project store tests to use the windowed sub-tree shape.

## Tests

- RED: `npm run test:unit -- src/api/client.athenaEvolutionPlan.test.ts -t "getOutline|getStoryline"`
- GREEN: `npm run test:unit -- src/api/client.athenaEvolutionPlan.test.ts -t "getOutline|getStoryline"`
- GREEN: `npm run test:unit -- src/api/client.athenaEvolutionPlan.test.ts src/stores/project.workspace.test.ts src/components/shared/ProjectDashboard.test.ts`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` (`593 passed`)
- GREEN: `npm run build` from `frontend`
- GREEN: `npm run test:unit` from `frontend` (`405 passed`)
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Frontend outline/storyline refresh paths now reuse the bounded Athena evolution
plan window instead of calling deprecated full JSON endpoints. This keeps both
Hermes cold start and later explicit refreshes aligned with thousand-chapter UI
constraints.
