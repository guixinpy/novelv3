# Phase 249 - Direct Chapter Jump for Windowed Narrative Plans

## Goal

Improve long-form chapter navigation in Athena narrative planning. Server-windowed
plans only load a slice of chapters, so the existing jump dropdown could not
reach distant chapters such as chapter 876 without paging many times.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/components/athena/NarrativeWorkbench.test.ts -t "direct chapter window"`
  - Failed because `[data-testid="chapter-direct-jump"]` did not exist.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `npm run test:unit -- --run src/components/athena/NarrativeWorkbench.test.ts`
    passed with `18 passed`.

## Changes

- Added a numeric chapter jump input and submit button to the chapter workbench.
- For server-windowed plans, direct jump emits `loadChapterWindow` with an offset
  anchored at the requested chapter.
- For fully loaded plans, direct jump keeps the existing local windowing behavior
  and scrolls the active chapter into view.
- Added clamping to keep requested chapter numbers within the known plan total.

## Verification Evidence

Fresh verification after the UI/layout adjustment:

- `npm run test:unit -- --run src/components/athena/NarrativeWorkbench.test.ts -t "direct chapter window"` passed with `1 passed`.
- `npm run build` passed.
- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `646 passed`.
- `npm run test:unit -- --run` passed with `415 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
