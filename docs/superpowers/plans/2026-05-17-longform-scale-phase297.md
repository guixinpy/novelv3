# Longform Scale Phase 297 - Remove Writing Poll Ceiling

## Goal

Support very long continuous writing sessions by keeping the frontend attached to an active writing background task beyond the previous 30 minute polling ceiling.

## Finding

The project store stopped polling writing tasks after `30 * 60` attempts. A 1000 chapter generation run can exceed 30 minutes, leaving the UI unable to refresh the final writing state when the backend task completes or fails later.

## TDD Evidence

RED:

```powershell
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "30 分钟"
```

Observed failure:

```text
expected "spy" to be called 1801 times, but got 1800 times
```

GREEN:

```powershell
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "30 分钟"
```

Observed result:

```text
1 passed, 29 skipped
```

## Change

- Removed the fixed 30 minute polling cap in `frontend/src/stores/project.ts`.
- Kept the existing project-scope guard, so polling exits when the user leaves or switches the current project.
- Added a regression test proving completion after the former 1800-poll ceiling still refreshes writing state.

## Verification

Pending full phase gate:

- Backend pytest
- Frontend build
- Frontend unit tests
- `git diff --check`
- DeepSeek key scan
