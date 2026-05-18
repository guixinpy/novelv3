# Phase 230: Project Snapshot Chapter Existence

## Goal

Avoid loading full chapter content when the world-model snapshot endpoint only needs to validate that a chapter index exists.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py::test_world_model_snapshot_chapter_existence_check_skips_content -q`
  - Failed because the existence check selected `chapter_contents.content`.
- GREEN: same targeted test passes after projecting only `ChapterContent.id`.

## Notes

- `GET /api/v1/projects/{project_id}/world-model/snapshot` still returns 404 for missing chapters.
- Snapshot projection behavior is unchanged.
