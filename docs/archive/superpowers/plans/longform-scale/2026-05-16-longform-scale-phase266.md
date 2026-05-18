# Longform Scale Phase 266 - Frontend Refreshes Writing State After Chapter Generation

## Goal

Keep the current Hermes session aligned after manual chapter generation. Backend chapter generation now syncs `writing_states`; the project store must refresh that state without requiring a page reload.

## Scope

- Refresh writing state after `project.generateChapter()`.
- Keep chapter generation successful even if the secondary writing-state refresh fails.

## RED

- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "generateChapter"`
  - Failed because `api.getWritingState` was not called after `generateChapter`.

## GREEN

- `npm run test:unit -- --run src/stores/project.workspace.test.ts -t "generateChapter"`
  - `1 passed`, `22 skipped`

## Related Verification

- `npm run test:unit -- --run src/stores/project.workspace.test.ts`
  - `23 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `656 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `62 passed`, `425 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
