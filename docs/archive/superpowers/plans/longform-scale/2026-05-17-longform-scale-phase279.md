# Longform Scale Phase 279 - Outline Target Reconciliation

## Objective

Keep writing progress aligned when a project relies on outline `total_chapters` as its effective target. Long-form projects are often replanned by regenerating the outline, so shortening or extending the outline must update `writing_state` just like editing `Project.target_chapter_count`.

## Scope

- Added writing-state target reconciliation after successful outline generation.
- Reused `WritingStateService.reconcile_target()` so project targets and outline fallback targets share the same boundary behavior.
- Added regression coverage for both outline target extension and shortening.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py -q -k "outline_target"`
  - Failed because extending an outline left writing status as `completed`, and shortening an outline left it as `running`.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py -q -k "outline_target"`
  - `2 passed, 9 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_outlines.py backend\tests\test_athena_evolution_generation_windows.py backend\tests\test_writing.py backend\tests\test_chapters.py backend\tests\test_projects.py -q`
  - `74 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `674 passed in 66.87s`.
- `npm run build` in `frontend`
  - Passed (`vue-tsc --noEmit && vite build`).
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `432 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.
