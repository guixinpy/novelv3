# Longform Scale Phase 60

## Goal

Cap retrieval embedding request batch sizes so remote providers do not receive unbounded input lists during large index rebuilds.

## Success Criteria

1. Pending retrieval embeddings are split into batches no larger than `RETRIEVAL_EMBEDDING_BATCH_SIZE`.
2. Small source batches still use one embedding call when under the cap.
3. Retrieval counts and search behavior remain unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that forces a small batch cap and observes provider call sizes.
2. Add a batch-size constant and helper that slices pending embedding payloads.
3. Use the helper inside `_flush_index_write_batch`.
4. Run targeted retrieval tests, a 1000-chapter smoke timing check, then full verification.
