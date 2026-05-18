# Longform Scale Phase 54

## Goal

Reduce retrieval indexing write overhead by avoiding per-document and per-chunk flushes.

## Success Criteria

1. New retrieval documents and chunks receive application-generated IDs.
2. New retrieval documents, chunks, terms, and embeddings are written in batches.
3. Full reindex of a new project does not call `Session.flush()` once per document or chunk.
4. Existing retrieval search and diagnostics tests continue to pass.
5. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that counts flush calls during full reindex of a new project.
2. Generate IDs before insert and replace per-row `add/flush` with bulk saves.
3. Run targeted tests, full verification, and a 1000-chapter smoke timing check.
