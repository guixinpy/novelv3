# Phase 146 - Retrieval write batch scaling guard

## Goal

Reduce retrieval reindex write overhead while bounding batch memory for long, varied prose.

## Why

The 1,000-chapter smoke profile showed retrieval reindex dominated by SQLite write batches for chunks, embeddings, and lexical terms. Larger source batches reduce small executemany overhead, but real novel text can produce many unique lexical terms per chunk, so batching must also have a term-row guard.

## TDD

RED:

- Added `test_reindex_flushes_write_batch_when_term_rows_reach_guard`.
- The test failed because there was no `INDEX_WRITE_BATCH_MAX_TERMS` threshold and flushes were controlled only by source count.

GREEN:

- Raised `INDEX_WRITE_BATCH_SOURCES` from 100 to 500.
- Added `INDEX_WRITE_BATCH_MAX_TERMS = 50_000`.
- Added `_should_flush_index_write_batch(...)` so indexing flushes on either source count or term-row count.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py::test_reindex_flushes_write_batch_when_term_rows_reach_guard -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py::test_reindex_uses_configured_write_batches_for_many_sources backend\tests\test_athena_retrieval.py::test_reindex_batches_retrieval_rows_as_core_inserts -q` -> 2 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py -q` -> 37 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 8,913 ms, elapsed 9,682 ms
