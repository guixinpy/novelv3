# Phase 163 - Wire storyline milestone windows

## Goal

Connect the Athena storyline view to the milestone window support added in Phase 162.

## Why

In long serial novels, a main storyline can contain one node per chapter. The storyline tab must not render or request every milestone just to show the first screen.

## TDD

RED 1:

- Added a `NarrativeWorkbench` test for a server-windowed plotline with 80 loaded milestones and 250 total milestones.
- It failed because the component used local milestone counts and did not emit milestone window requests.

GREEN 1:

- `NarrativeWorkbench` now reads `milestones_total`, `milestones_offset`, `milestones_limit`, and `milestones_has_more`.
- Storyline milestone paging emits `loadMilestoneWindow` with `{ offset, limit }`.

RED 2:

- Added an `AthenaView` test that simulates a milestone window request from the workbench.
- It failed because the parent view did not handle the event.

GREEN 2:

- `AthenaView` handles `loadMilestoneWindow` and calls `athena.loadEvolutionPlan` with `mode: 'window'`, `plotline_limit: 20`, and milestone window params.

RED 3:

- Added a route-loader test requiring the storyline tab to load a bounded plotline/milestone window.
- It failed because the route still used the old full-plan path.

GREEN 3:

- `athenaSectionLoader` now loads the storyline tab with `plotline_limit: 20` and `milestone_limit: 80`.

## Verification

- `npm run test:unit -- NarrativeWorkbench` -> 17 passed
- `npm run test:unit -- AthenaView` -> 8 passed
- `npm run test:unit -- athenaSectionLoader` -> 19 passed
- `npm run test:unit` -> 61 files / 393 tests passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed
