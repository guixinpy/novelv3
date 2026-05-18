# Phase 107 - Light Longform Evidence Chapter Counts

## Goal
Keep longform evidence-range context construction cheap for million-word projects with large chapter bodies.

## Changes
- Longform evidence-range chapter totals now use explicit `count(ChapterContent.id)`.
- Existing longform memory grouping, current word-count sum, and context block text remain unchanged.

## Verification
- Added SQL-level regression coverage proving the chapter count query does not select `ChapterContent.content`.
- Re-ran longform evidence-range focused tests.
- Re-ran the complete longform scale test file: `33 passed`.
- Re-ran the full backend pytest suite: `532 passed`.
