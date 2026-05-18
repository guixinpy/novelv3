# Phase 176 - Cache Local Embedding Token Features

## Problem

The local hash embedding provider already tokenized each chunk once, but it still
recomputed hash features for the same token across chunks and embedding batches.
Million-word projects repeatedly contain the same names, places, and genre terms, so
this added avoidable CPU work during retrieval reindex.

## Change

- Added an LRU cache for local token hash features keyed by token and vector
  dimension.
- Kept remote embedding providers unchanged.
- Preserved the existing single-chunk repeated-token behavior through `Counter`.

## Tests

- RED: `backend/tests/test_athena_retrieval.py::test_local_hash_embedding_reuses_token_hashes_across_batches`
- GREEN: local embedding cache target tests
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py -q`
- GREEN: `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

The 1000-chapter smoke test still passed at 1,000,000 synthetic words. Retrieval
reindex timing improved from the previous 8,930 ms observation to 7,994 ms in this
run.
