# Phase 158 - Key narrative plan store cache by query

## Goal

Keep full and windowed Athena narrative plan responses isolated in the frontend store.

## Why

The API can now return bounded narrative plan windows. The store still held a single `evolutionPlan` value behind one `evolution-plan` cache key, so a later full-view request could reuse a previous windowed response, or a slower old request could overwrite newer view data.

## TDD

RED 1:

- Added a store test that loads a windowed plan and then a full plan for the same project.
- It failed because the second load reused the existing cached value and only called `getAthenaEvolutionPlan` once.

GREEN 1:

- Added typed `loadEvolutionPlan(projectId, params?)`.
- Built deterministic resource keys from plan query parameters.
- Stored the resource key alongside `evolutionPlan`, so only the matching cached response is considered loaded.

RED 2:

- Added a concurrent request test where an old window request resolves after a newer full request.
- It failed because the old response overwrote the newer full response.

GREEN 2:

- Added an evolution-plan request sequence guard.
- Only the latest issued plan request may write to the store.

## Verification

- `npm run test:unit -- athena.scope` -> 11 passed
- `npm run test:unit` -> 61 files / 379 tests passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed
