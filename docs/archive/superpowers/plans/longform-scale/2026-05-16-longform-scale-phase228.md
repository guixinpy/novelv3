# Phase 228: Bound Retrieval Fallback Chapter Preview

## Goal

Avoid loading a full previous chapter body when retrieval context only needs a short fallback query preview.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_retrieval.py::test_chapter_context_fallback_projects_previous_chapter_preview -q`
  - Failed because the fallback query did not use `substr(chapter_contents.content)`.
- GREEN: same targeted test passes after projecting only the previous chapter preview.

## Notes

- `_chapter_context_query()` now uses a 500-character SQL projection when no outline chapter is available.
- Retrieval indexing and normal outline-based query construction are unchanged.
