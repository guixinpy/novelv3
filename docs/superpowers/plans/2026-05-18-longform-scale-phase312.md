# Longform Scale Phase 312 - Surface Longform Trace Diagnostics

## Goal

Make longform generation diagnostics readable in the model-call detail drawer.

## Finding

Phases 310 and 311 added backend trace metadata for chapter word-target drift and post-generation maintenance warnings. The frontend still required users to inspect raw JSON, which is too slow when diagnosing long writing runs.

## TDD Evidence

RED:

```powershell
npm run test:unit -- --run src/components/modelTrace/ModelTraceDrawer.test.ts
```

Observed failure:

```text
expected null not to be null
```

GREEN:

```powershell
npm run test:unit -- --run src/components/modelTrace/ModelTraceDrawer.test.ts
```

Observed result:

```text
9 passed
```

## Change

- The model-call detail drawer now renders a `长篇生成诊断` section when trace metadata includes longform diagnostics.
- Chapter word-target drift is shown as actual vs target, target range, deviation, and Chinese status label.
- Post-generation warnings are shown as stage, error type, and sanitized message.
- Raw metadata remains available for deeper debugging.

## Verification

Stage gate:

- `npm run test:unit -- --run src/components/modelTrace/ModelTraceDrawer.test.ts` -> `9 passed`
- `npm run build` -> passed
- Browser check with mocked manuscript trace -> rendered `长篇生成诊断`, `13字 / 目标10字`, `偏长`, `长篇记忆刷新`, and `maintenance failed`

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `703 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `444 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
