# Longform Scale Phase 276 - Final Chapter Completion State

## Objective

Make writing state immediately reflect project completion after the final target chapter is generated. Before this phase, generating the last planned chapter advanced the pointer to the next chapter but left the state as `idle`, so the dashboard could still imply the project was ready to continue.

## Scope

- Centralized final-target completion logic in `WritingStateService.complete_chapter()`.
- The service now resolves the project and uses the shared chapter target guard from Phase 275.
- If the next chapter pointer is beyond the effective target, the writing state becomes `completed`.
- This applies to direct generation, background generation, and retry completion paths because they already call `complete_chapter()`.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q -k "final and target"`
  - Failed because both project-target and outline-target final chapter generation left writing state as `idle`.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py -q -k "final and target"`
  - `2 passed, 31 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_writing.py -q`
  - `47 passed`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `668 passed in 56.81s`.
- `npm run build` in `frontend`
  - `vue-tsc --noEmit && vite build` completed successfully.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`, `432 passed`.
- `git diff --check`
  - Passed with no output.
- DeepSeek key scan
  - `NO_MATCH`.
