# Phase 229: Target Changed Retrieval Sources

## Goal

Avoid scanning every project source a second time when retrieval reindex only needs to rebuild a small changed subset.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_retrieval.py::test_reindex_fetches_changed_chapter_sources_by_id -q`
  - Failed because the changed-source rebuild path selected chapter bodies with a second broad project scan.
- GREEN: same targeted test passes after `_project_sources_by_key()` queries source rows by type and source id.

## Notes

- The first reindex pass still scans current sources to compare hashes and detect removals.
- The rebuild pass now fetches only requested chapter, longform-memory, and world-fact rows.
- Source id lookups are batched to avoid oversized SQL `IN` clauses.
