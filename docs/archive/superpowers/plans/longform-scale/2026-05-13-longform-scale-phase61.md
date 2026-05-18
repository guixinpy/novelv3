# Longform Scale Phase 61

## Goal

Reduce retrieval reindex object construction overhead by inserting all retrieval index tables from mapping rows.

## Success Criteria

1. Retrieval documents, chunks, terms, and embeddings all use `bulk_insert_mappings`.
2. `bulk_save_objects` is no longer used for retrieval index rows in `_flush_index_write_batch`.
3. Retrieval row counts, search behavior, and embedding batch behavior remain unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Update the batching regression test to observe mapping inserts for all retrieval tables.
2. Convert document and chunk buffers from ORM instances to mapping dictionaries.
3. Convert generated embedding rows to mapping dictionaries.
4. Run targeted retrieval tests, a 1000-chapter smoke timing check, then full verification.
