# Phase 142 - Project list avoids chapter aggregation

## Goal

Keep `/api/v1/projects` lightweight by returning stored project summaries instead of reconciling chapter word counts for every project on each list request.

## Why

For long-form use, one project can contain 1000+ chapters and 1M+ words. A project index page should not run chapter-table `SUM(...)` scans across every project just to render summary cards. Precise word-count reconciliation remains available on project detail/update paths.

## TDD

RED:

- `test_list_projects_does_not_reconcile_chapter_word_counts` set a cached `current_word_count`, added chapters, then called the project list endpoint.
- It failed because the list endpoint recalculated the chapter sum and changed the cached value.

GREEN:

- Removed per-project `reconcile_project_word_count(...)` from `list_projects`.
- `GET /api/v1/projects` now reads project rows directly, preserving cached summary fields.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py::test_list_projects_does_not_reconcile_chapter_word_counts -q`
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_projects.py -q`
