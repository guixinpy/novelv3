# Longform Scale Phase 296 - Finish Project Status Sync

## Assumption

When writing is already beyond the effective chapter target, start/resume should mark the whole project complete without creating another task.

## Risk

`WritingStateService.finish_project()` only updated `writing_states`. If project status had drifted or had never been synced by `complete_chapter()`, the dashboard could show writing completed while the project list still showed draft/writing.

## Change

1. `finish_project()` now updates `Project.status` to `completed`.
2. `finish_project()` keeps `Project.current_phase` at `content`.

## Verification

- Red: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_writing.py::test_writing_start_finish_project_syncs_project_status -q` failed because project status stayed `draft`.
- Green: `backend\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\test_writing.py backend\\tests\\test_projects.py backend\\tests\\test_outlines.py -q` passed with 47 tests.
- Full verification will run before commit.
