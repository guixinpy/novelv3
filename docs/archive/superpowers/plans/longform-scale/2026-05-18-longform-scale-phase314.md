# Longform Scale Phase 314 - Show Word Target Drift In Athena Overview

## Goal

Make project-level chapter word-count drift visible from Athena overview.

## Finding

Phase 313 added backend aggregate diagnostics, but the overview still only showed memory/retrieval maintenance. Users need to see whether the project is accumulating short or long chapters without opening individual chapter traces.

## TDD Evidence

RED:

```powershell
npm run test:unit -- --run src/components/athena/AthenaOverview.test.ts
```

Observed failure:

```text
expected ... to contain '字数节奏'
```

GREEN:

```powershell
npm run test:unit -- --run src/components/athena/AthenaOverview.test.ts
```

Observed result:

```text
9 passed
```

## Change

- Athena overview now shows `字数节奏` when longform maintenance diagnostics include word-target data.
- The summary displays target average, target range, under/within/over counts, and limited under/over chapter indexes.
- Existing maintenance status and repair controls are unchanged.

## Verification

Stage gate:

- `npm run test:unit -- --run src/components/athena/AthenaOverview.test.ts` -> `9 passed`

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `704 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `445 passed`
- Browser check with mocked Athena overview diagnostics -> rendered `字数节奏`, `目标 100字`, `范围 85-115字`, `偏短章节：1`, and `偏长章节：3`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
