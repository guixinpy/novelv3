# Longform Scale Phase 269 - Retry Chapter Refresh Targets

## Goal

Make `retry_chapter` background tasks refresh the same visible writing surfaces as normal chapter generation. A failed longform chapter retry should update content, versions, and writing progress without relying on a manual reload.

## Scope

- Map `retry_chapter` to the content panel in backend UI hints.
- Give `retry_chapter` the refresh targets `project`, `content`, `versions`, and `writing_state`.
- Mirror the mapping in frontend workspace metadata for any dialog/action path that reports `retry_chapter`.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q -k "retry_chapter_refreshes"`
  - Failed because `retry_chapter` returned no content target panel.
- `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts -t "retry_chapter"`
  - Failed because `getActionPanel("retry_chapter")` returned `null`.

## GREEN

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py -q -k "retry_chapter_refreshes"`
  - `1 passed`, `30 deselected`
- `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts -t "retry_chapter"`
  - `1 passed`, `1 skipped`

## Related Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_background.py backend\tests\test_writing.py -q`
  - `39 passed`
- `npm run test:unit -- --run src/components/workspace/workspaceMeta.test.ts src/stores/project.workspace.test.ts`
  - `26 passed`

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `658 passed`
- `npm run build`
  - `vue-tsc --noEmit && vite build` passed
- `npm run test:unit -- --run`
  - `64 passed`, `430 passed`
- `git diff --check`
  - Passed
- DeepSeek key scan
  - `NO_MATCH`
