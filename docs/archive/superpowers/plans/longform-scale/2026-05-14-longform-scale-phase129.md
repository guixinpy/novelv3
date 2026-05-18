# Phase 129 - Preserve Chapter Ending Clues in Longform Memory

## Goal
Improve longform writing continuity by keeping chapter-ending twists, reveals, and foreshadowing in chapter memory summaries.

## Problem
Chapter memories used a fixed prefix preview of chapter content. In web-novel chapters, important reveals often happen at the end of the chapter, so later generation could miss critical continuity details even though the chapter memory existed.

## Changes
- Added a bounded chapter-content preview that keeps both the opening and ending of long chapter text.
- Short chapter text is still preserved directly.
- Existing memory summary size stays bounded at the same call-site limit.

## Verification
- Added a regression test that failed before the fix: a chapter-ending clue was absent from chapter memory.
- Re-ran longform scale tests: `35 passed`.
- Re-ran Athena retrieval tests: `36 passed`.
- Re-ran the full backend suite: `552 passed`.
- Re-ran 1000 chapter / 1,000,000 word smoke: `memory_rebuild=328 ms`, `retrieval_reindex=8435 ms`, `context_build=317 ms`, `prompt_context_chars=3747`.
