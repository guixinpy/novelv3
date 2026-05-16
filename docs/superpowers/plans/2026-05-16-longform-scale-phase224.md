# Phase 224: Bound Athena Manuscript Recent Excerpts

## Goal

Avoid loading full chapter bodies when building Athena manuscript progress context for recent chapter excerpts.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_dialog.py::test_athena_manuscript_context_projects_recent_excerpt_content -q`
  - Failed because the recent excerpt query did not use `substr(chapter_contents.content)`.
- GREEN: same targeted test passes after projecting only the recent content preview.

## Notes

- Existing manuscript summary output remains unchanged.
- The query now loads id, chapter index, title, and a bounded content preview.
