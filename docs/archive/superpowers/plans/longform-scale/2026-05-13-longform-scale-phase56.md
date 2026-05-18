# Longform Scale Phase 56

## Goal

Reduce retrieval reindex database round trips by batching writes across multiple sources.

## Success Criteria

1. Multiple retrieval sources are written in shared batches for documents, chunks, terms, and embeddings.
2. Batch writes remain bounded by a configurable source batch size.
3. Existing retrieval counts and search behavior stay unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that observes cross-source bulk write calls.
2. Add a small in-memory retrieval index batch buffer.
3. Flush the buffer by source batch size and at the end.
4. Run targeted tests, full verification, and a 1000-chapter smoke timing check.
