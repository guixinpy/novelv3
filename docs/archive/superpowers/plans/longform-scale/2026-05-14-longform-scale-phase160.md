# Phase 160 - Wire chapter narrative plan windows

## Goal

Make the Athena narrative chapter view load and page chapter plans through bounded server windows instead of requiring a full narrative plan upfront.

## Why

For thousand-chapter novels, the chapter planning view must not depend on loading every outline chapter at once. Phase 156-159 added backend, client, store, and total-count support. This phase connects the first UI path to that windowed data flow.

## TDD

RED 1:

- Added a `NarrativeWorkbench` test for a plan with `chapters_offset`, `chapters_limit`, and `chapters_total`.
- It failed because the component rendered local-window labels only and had no chapter window event.

GREEN 1:

- `NarrativeWorkbench` now recognizes server-windowed chapter plans.
- It shows `当前显示第X-Y章 / 共Z章`.
- Chapter previous/next emits `loadChapterWindow` with `{ offset, limit }`.

RED 2:

- Added an `AthenaView` test that simulates the workbench requesting a later chapter window.
- It failed because the parent view did not handle the event.

GREEN 2:

- `AthenaView` handles chapter window requests and calls `athena.loadEvolutionPlan` with `mode: 'window'`.

RED 3:

- Added route-loader tests requiring the chapters view to load the first 50-chapter window and graph view to request the full plan even after a windowed plan exists.

GREEN 3:

- `athenaSectionLoader` loads `{ mode: 'window', chapter_offset: 0, chapter_limit: 50 }` for the chapters view.
- Graph view always asks the store for the full plan, letting the store cache decide whether a network call is needed.

## Verification

- `npm run test:unit -- NarrativeWorkbench` -> 15 passed
- `npm run test:unit -- AthenaView` -> 6 passed
- `npm run test:unit -- athenaSectionLoader` -> 17 passed
- `npm run test:unit` -> 61 files / 385 tests passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed
