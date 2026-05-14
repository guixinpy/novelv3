# Phase 165 - Restore manuscript position in long chapter lists

## Goal

Keep the manuscript editor anchored to the user's last edited chapter even when the project has hundreds or thousands of chapters.

## Why

The manuscript view loads chapter summaries in windows. Before this phase, returning to a 1000-chapter project with the last edited chapter at chapter 900 loaded only the first summary page and fell back to chapter 1. That breaks longform writing continuity.

## TDD

RED:

- Added a `ManuscriptView` test where the workspace remembers chapter 900 while the initial summary page contains chapters 1-200.
- It failed because initialization made only one chapter-list request and selected from the first page.

GREEN:

- `ManuscriptView` now detects when the remembered chapter is outside the loaded summary window.
- It calculates a bounded window offset around the remembered chapter and reloads chapter summaries before selecting.
- The test mock setup now resets queued mock implementations between tests to avoid order coupling.

## Verification

- `npm run test:unit -- ManuscriptView` -> 7 passed
