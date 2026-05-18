# Phase 157 - Type windowed narrative plan API client

## Goal

Expose the new windowed narrative plan backend mode through the frontend API layer without changing UI behavior yet.

## Why

The backend can now return bounded narrative plan windows. Before wiring UI views to server-side windows, the client needs typed query parameters and response metadata so later changes can be incremental and testable.

## TDD

RED:

- Added an API client test for `getAthenaEvolutionPlan(projectId, windowParams)`.
- The test asserts all window query parameters are serialized into the request URL.
- It failed because the old client always requested `/athena/evolution/plan` without query parameters.

GREEN:

- Added `AthenaEvolutionPlanQuery`.
- Extended `AthenaEvolutionPlan` with optional window metadata fields.
- `getAthenaEvolutionPlan` now serializes `mode`, chapter, plotline, and foreshadowing window parameters.

## Verification

- `npm run test:unit -- client.athenaEvolutionPlan` -> 1 passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed
- `npm run test:unit` -> 61 files / 377 tests passed
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
