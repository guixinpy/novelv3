# Phase 330: Gate Outline-Like Output In Longform Smoke

## Goal

Extend the longform smoke gate so synthetic thousand-chapter runs can fail when continuous writing produces outline-like chapter output.

## Scope

- Add CLI flag `--max-writing-outline-like`.
- Read `writing_worker.generation_diagnostics.prose_quality.outline_like_count`.
- Fail the smoke command when outline-like output exceeds the threshold.
- Document the new quality gate in stability mechanisms.

## Verification

- RED confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_writing_diagnostics_exceed_limits -q`
  - Failed because the CLI did not recognize `--max-writing-outline-like`.
- GREEN confirmed:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_scale_smoke_reports_writing_worker_range backend\tests\test_longform_scale.py::test_longform_scale_smoke_cli_fails_when_writing_diagnostics_exceed_limits -q`
  - `2 passed`
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q`
  - `49 passed`
- CLI smoke confirmed:
  - `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 5 --words-per-chapter 80 --target-chapter 5 --cleanup --max-writing-under-target 0 --max-writing-over-target 0 --max-writing-warnings 0 --max-writing-outline-like 0`
  - Passed with `writing_worker.generation_diagnostics.prose_quality.outline_like_count = 0`.

## Standard Gate Addition

Recommended smoke command should include:

```powershell
--max-writing-outline-like 0
```
