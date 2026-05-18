# Phase 161 - Wire foreshadowing narrative plan windows

## Goal

Make the Athena foreshadowing view load and page foreshadowing records through bounded server windows.

## Why

Long serial novels can accumulate hundreds or thousands of planted and resolved foreshadowing records. The UI should not require the full narrative plan payload just to inspect the foreshadowing tab.

## TDD

RED 1:

- Added a `NarrativeWorkbench` test for `foreshadowing_offset`, `foreshadowing_limit`, and `foreshadowing_total`.
- It failed because the component hid paging controls when exactly one local page was loaded and had no foreshadowing window event.

GREEN 1:

- `NarrativeWorkbench` recognizes server-windowed foreshadowing data.
- It shows `当前显示 X-Y / Z 条伏笔`.
- Previous/next emits `loadForeshadowingWindow` with `{ offset, limit }`.

RED 2:

- Added an `AthenaView` test that simulates a foreshadowing window request from the workbench.
- It failed because the parent did not handle that event.

GREEN 2:

- `AthenaView` handles `loadForeshadowingWindow` and calls `athena.loadEvolutionPlan` with `mode: 'window'`.

RED 3:

- Added a route-loader test requiring the foreshadowing tab to load the first 100-record window.
- It failed because foreshadowing still used the full-plan path.

GREEN 3:

- `athenaSectionLoader` now loads a bounded foreshadowing window for the foreshadowing tab.

## Verification

- `npm run test:unit -- NarrativeWorkbench` -> 16 passed
- `npm run test:unit -- AthenaView` -> 7 passed
- `npm run test:unit -- athenaSectionLoader` -> 18 passed
- `npm run test:unit` -> 61 files / 388 tests passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed
