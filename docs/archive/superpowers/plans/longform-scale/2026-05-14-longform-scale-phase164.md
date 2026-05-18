# Phase 164 - Preserve retrieval documents across memory rebuilds

## Goal

Avoid rebuilding unchanged retrieval documents after longform memory rows are regenerated.

## Why

Longform memory rebuilds replace `LongformMemory.id` values. Retrieval documents previously matched existing rows by `source_id`, so unchanged memory sources such as `memory:chapter:500` were treated as new documents after a rebuild. On a 1000-chapter project this could force more than 1000 memory retrieval documents to be re-chunked and re-embedded unnecessarily.

## TDD

RED:

- Added a retrieval test that rebuilds longform memory twice with unchanged chapter content.
- It failed because the second reindex rebuilt all memory retrieval documents.

GREEN:

- `reindex_project_retrieval` now falls back to stable `source_ref` when `source_id` changed.
- Preserved documents update their `source_id` to the current source row without rebuilding chunks, terms, or embeddings.
- Stale cleanup now tracks matched document ids so a ref-matched preserved document is not deleted later.

## Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py::test_reindex_preserves_memory_documents_after_memory_rebuild backend\tests\test_athena_retrieval.py::test_reindex_existing_document_scan_projects_only_preservation_fields -q` -> 2 passed
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_retrieval.py -q` -> 38 passed
- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q` -> 37 passed
- 1000 chapter / 1,000,000 word smoke follow-up: first retrieval reindex 13608 ms; memory rebuild then reindex 245 ms; second reindex indexed 0 documents and preserved 2061 documents.
