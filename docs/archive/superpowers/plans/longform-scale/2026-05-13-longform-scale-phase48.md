# Longform Scale Phase 48

## Goal

Keep the 1000-chapter scale smoke report auditable when background task progress has already been compacted.

## Success Criteria

1. `_compact_progress` preserves compact checkpoint fields without re-expanding chapter indexes.
2. Existing reports still omit `completed_chapter_indexes`.
3. Targeted regression test fails before the fix and passes after the fix.
4. Backend, frontend unit tests, typecheck, build, diff check, and secret scans pass before commit.

## Steps

1. Add a regression test for compact progress fields.
2. Preserve `completed_until_chapter_index`, `first_completed_chapter_index`, and `last_completed_chapter_index` when they already exist in progress.
3. Run targeted test, then full verification.
