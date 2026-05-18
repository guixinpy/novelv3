# Longform Scale Phase 210 - Stream Retrieval Reindex Sources

## Goal

Reduce memory peaks during full Athena retrieval rebuilds for thousand-chapter projects.

## Problem

`reindex_project_retrieval()` previously collected every pending `RetrievalSource` into a list before calling `_index_sources()`. For long projects this list can hold many full chapter bodies in memory at once, even though `_index_sources()` already accepts any iterable.

## Change

- First pass over project sources now collects only lightweight `(source_type, source_id)` keys for stale or missing retrieval documents.
- Stale documents are deleted before indexing as before.
- The second pass streams matching sources through `_project_sources_by_key()` into `_index_sources()`.
- Preserved retrieval documents and source-id refresh behavior remain unchanged.

## Regression Test

- `test_reindex_streams_pending_sources_to_indexer` verifies `reindex_project_retrieval()` no longer passes a list of full sources to `_index_sources()`.

## Verification

Initial verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_retrieval.py::test_reindex_streams_pending_sources_to_indexer -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_retrieval.py backend/tests/test_longform_scale.py -q
```

Results:

- Regression test: `1 passed`
- Retrieval and longform scale tests: `80 passed`

Full verification is run before commit.
