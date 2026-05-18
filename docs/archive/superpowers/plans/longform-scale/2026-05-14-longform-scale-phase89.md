# Longform Scale Phase 89: Subquery Cleanup for Chapter Retrieval Reindex

## Goal

Keep incremental retrieval indexing stable for long chapters. When a generated chapter is re-indexed, deleting old retrieval chunks must not materialize all old chunk ids in Python.

## Change

- Added a regression test for re-indexing the same chapter with multiple retrieval chunks.
- Changed `_delete_document` to delete terms, embeddings, chunks, and document rows through document id subqueries.
- Removed the old object-based deletion helper that loaded chunk ids into a Python list.

## Verification

- Red: `python -m pytest backend/tests/test_athena_retrieval.py -k "materializing_chunk_ids" -q --basetemp .tmp/pytest`
- Green: same focused command.
- Retrieval suite: `python -m pytest backend/tests/test_athena_retrieval.py -q --basetemp .tmp/pytest`
