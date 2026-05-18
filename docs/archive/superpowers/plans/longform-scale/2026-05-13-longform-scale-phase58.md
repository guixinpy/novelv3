# Longform Scale Phase 58

## Goal

Reduce retrieval reindex Python overhead by inserting lexical terms as bulk mappings instead of constructing ORM objects for the largest retrieval table.

## Success Criteria

1. Retrieval term rows are written through `bulk_insert_mappings`.
2. Retrieval documents, chunks, and embeddings keep the existing batched write path.
3. Retrieval term counts and search behavior remain unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that observes `bulk_insert_mappings(RetrievalTerm, ...)`.
2. Change `_index_sources` to buffer term dictionaries with explicit ids.
3. Change `_flush_index_write_batch` to bulk insert term mappings.
4. Run targeted retrieval tests, a 1000-chapter smoke timing check, then full verification.
