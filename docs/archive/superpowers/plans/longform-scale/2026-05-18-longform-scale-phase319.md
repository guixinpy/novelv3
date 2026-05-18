# Longform Scale Phase 319 - Gate Smoke Writing Diagnostics

## Goal

Let the longform scale smoke CLI fail when writing worker diagnostics exceed configured quality thresholds.

## Finding

Phase 318 made writing diagnostics visible in the smoke report, but a CI run would still pass unless a human inspected the JSON. Longform stability needs machine-enforced thresholds for short chapters, long chapters, and post-generation maintenance warnings.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_writing_diagnostics_exceed_limits -q
```

Observed failure:

```text
unrecognized arguments: --max-writing-under-target ... --max-writing-over-target ... --max-writing-warnings ...
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_writing_diagnostics_exceed_limits backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_thresholds_are_exceeded -q
```

Observed result:

```text
2 passed
```

## Change

- Added CLI thresholds:
  - `--max-writing-under-target`
  - `--max-writing-over-target`
  - `--max-writing-warnings`
- `_threshold_failures()` now checks `writing_worker.generation_diagnostics`.
- Missing writing worker diagnostics now fail when a writing worker report exists.

## Verification

Stage gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q` -> `48 passed`

Full gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `707 passed`
- `npm run build` in `frontend` -> passed
- `npm run test:unit -- --run` in `frontend` -> `447 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
