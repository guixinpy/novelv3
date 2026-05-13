# Longform Scale Phase 62

## Goal

Keep chapter-range background task progress updates stable after checkpoint compaction by extending compacted sequential ranges without rebuilding full checkpoint lists.

## Success Criteria

1. A compacted sequential range can advance by one chapter without calling `_completed_chapter_index_set`.
2. The compacted progress payload remains compatible with retry/resume fields.
3. Existing non-compacted and retry behavior remains unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that monkeypatches checkpoint expansion to fail after compaction.
2. Add a fast path in `mark_range_progress` for compacted sequential progress.
3. Keep existing fallback behavior for sparse or nonsequential progress.
4. Run targeted background and longform smoke tests, then full verification.
