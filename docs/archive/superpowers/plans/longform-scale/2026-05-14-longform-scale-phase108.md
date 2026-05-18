# Phase 108 - Light Longform Diagnostics Chapter Counts

## Goal
Keep longform memory diagnostics responsive when projects contain large chapter bodies.

## Changes
- Longform memory diagnostics now compute `chapter_count` with explicit `count(ChapterContent.id)`.
- Existing memory-type grouping, word-count reconciliation, and diagnostics response shape are unchanged.

## Verification
- Added SQL-level regression coverage proving diagnostics chapter count queries do not select `ChapterContent.content`.
- Re-ran longform diagnostics focused tests.
- Re-ran the complete longform scale test file: `34 passed`.
- Re-ran the full backend pytest suite: `533 passed`.
