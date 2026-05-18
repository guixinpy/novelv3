# Longform Scale Phase 264 - Project Store Writing Controls

## Goal

Centralize writing-state loading and control in the project store. This gives Hermes and future writing controls one guarded state path instead of scattered direct API calls.

## Scope

- Add `loadWritingState`, `startWriting`, `pauseWriting`, and `resumeWriting` actions to the project store.
- Guard writing-state responses with the existing project request lane mechanism.
- Type writing control API calls as `WritingState`.

## RED

- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "writing state"`
  - Failed because `store.loadWritingState` did not exist.

## GREEN

- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "writing state"`
  - `2 passed`, `20 skipped`

## Related Verification

- `npm run test:unit -- --run src/stores/project.workspace.test.ts`
  - `22 passed`
- `npm run test:unit -- --run src/api/client.worldModel.test.ts`
  - `7 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `654 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `62 passed`, `424 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
