# Longform Scale Phase 59

## Goal

Batch retrieval embedding generation across source batches so large projects do not trigger one embedding provider call per document.

## Success Criteria

1. Multiple sources in one index write batch share a single `embed_texts` call.
2. Retrieval documents, chunks, terms, and embeddings keep the same persisted counts.
3. Existing retrieval search behavior remains unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that observes embedding provider batch sizes for multiple sources.
2. Add a pending embedding payload structure for chunk ids and text.
3. Move embedding generation into the index batch flush path.
4. Run targeted retrieval tests, a 1000-chapter smoke timing check, then full verification.
