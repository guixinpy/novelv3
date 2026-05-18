# Longform Scale Phase 317 - Surface Writing Range Progress

## Goal

Show continuous writing batch progress in Hermes instead of only showing the next chapter pointer.

## Finding

Compact background task polling already returns `result.progress`, and the store used it to update `writingState.current_chapter`. The UI still hid the actual batch progress. In a long writing run, "第 N 章" is not enough to answer how much of the current range has completed.

## TDD Evidence

RED:

```powershell
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "轮询到范围任务进度"
npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "range progress"
```

Observed failures:

```text
expected undefined to deeply equal { chapter_range: ... }
expected ... to contain '本轮进度'
```

GREEN:

```powershell
npm run test:unit -- --run src/stores/project.workspace.test.ts -t "轮询到范围任务进度"
npm run test:unit -- --run src/components/shared/ProjectDashboard.test.ts -t "range progress"
```

Observed result:

```text
1 passed
1 passed
```

## Change

- Added a typed `WritingTaskProgress` frontend API shape.
- The project store now preserves the latest compact writing task progress snapshot.
- Hermes passes the progress snapshot into the dashboard.
- The dashboard renders a compact "本轮进度" block with completed count, total count, percent, next chapter, and progress bar.

## Verification

Stage gate:

- `npm run test:unit -- --run src/stores/project.workspace.test.ts src/components/shared/ProjectDashboard.test.ts src/views/HermesView.test.ts` -> `44 passed`

Full gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `706 passed`
- `npm run build` in `frontend` -> passed
- `npm run test:unit -- --run` in `frontend` -> `447 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`

Browser smoke:

- Browser plugin tool was unavailable; Playwright fallback used local Chrome channel.
- `http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/hermes` rendered dashboard sections with no material failed responses and no page errors.
