# Longform Scale Phase 318 - Add Smoke Writing Diagnostics

## Goal

Include writing worker generation diagnostics in the longform scale smoke report.

## Finding

The writing worker smoke already verifies range progress and pending chapters, but it did not exercise the new per-task generation diagnostics path. A future regression could remove diagnostic aggregation while the smoke report still passed on progress alone.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range -q
```

Observed failure:

```text
KeyError: 'generation_diagnostics'
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range -q
```

Observed result:

```text
1 passed
```

## Change

- The writing worker smoke fake generation now writes lightweight successful model traces with `chapter_word_target` metadata.
- The existing writing worker aggregation path produces diagnostics during smoke runs.
- The smoke report now exposes `writing_worker.generation_diagnostics`.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py backend\tests\test_writing.py -q` -> `75 passed`

Full gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `706 passed`
- `npm run build` in `frontend` -> passed
- `npm run test:unit -- --run` in `frontend` -> `447 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
