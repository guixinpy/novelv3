# Longform Scale Phase 274 - Writing Target Boundary

## Objective

Prevent continuous writing controls from queuing chapter generation after the project has already reached its planned chapter count. This matters for 1000+ chapter projects because the system must stop deterministically at the configured boundary instead of drifting into chapter 1001+.

## Scope

- `POST /writing/start` now checks the current writing pointer before creating a `generate_chapter` background task.
- `POST /writing/resume` applies the same boundary before resuming queued generation.
- The effective chapter target is resolved from `Project.target_chapter_count`; if that is empty, it falls back to the latest outline `total_chapters`.
- When the pointer is beyond the effective target, the persisted writing state becomes `completed` and no background task is created.
- The dashboard renders writing `completed` as `已完成` and disables the writing control to avoid accidental restart.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "target"`
  - Failed because `/writing/start` and `/writing/resume` returned `running` after the target was already reached.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py -q -k "target"`
  - `2 passed, 12 deselected`.
- Related backend regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing.py backend\tests\test_chapters.py -q`
  - `43 passed`.
- RED: `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts`
  - Failed because the dashboard showed raw `completed` and still displayed the restart control.
- GREEN: `npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts`
  - `9 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `664 passed in 58.27s`.
- `npm run build` in `frontend`
  - `vue-tsc --noEmit && vite build` completed successfully.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`, `432 passed`.
- `git diff --check`
  - Passed with no output.
- DeepSeek key scan
  - `NO_MATCH`.
