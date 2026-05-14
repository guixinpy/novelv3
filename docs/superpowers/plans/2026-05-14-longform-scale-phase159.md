# Phase 159 - Render windowed narrative plan totals

## Goal

Prepare narrative views for windowed plan loading by showing total counts from backend metadata instead of the loaded window length.

## Why

Windowed narrative plans return only a bounded slice of chapters, plotlines, and foreshadowing items, plus total metadata. If UI metrics keep counting the returned arrays, a 1000-chapter plan loaded as a 50-chapter window looks like a 50-chapter plan.

## TDD

RED:

- Added a `NarrativeWorkbench` test with 50 loaded chapters, 2 loaded plotlines, 100 loaded foreshadowing items, and metadata totals of 1000, 4, and 300.
- Added an `AthenaView` timeline fallback summary test with the same windowed metadata.
- Both tests failed because the UI used array lengths.

GREEN:

- `NarrativeWorkbench` metrics now prefer `chapters_total`, `plotlines_total`, and `foreshadowing_total`.
- `AthenaView` timeline fallback summary uses the same total metadata and falls back to array lengths when metadata is absent.

## Verification

- `npm run test:unit -- NarrativeWorkbench` -> 14 passed
- `npm run test:unit -- AthenaView` -> 5 passed
- `npm run test:unit` -> 61 files / 381 tests passed
- `npx vue-tsc --noEmit` -> passed
- `npm run build` -> passed
