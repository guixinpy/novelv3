# Longform Scale Phase 286 - Validate Smoke Timing Stage Names

## Objective

Make longform smoke performance gates fail loudly when a timing stage threshold uses an unknown stage name. A misspelled `--max-stage-ms` should not silently pass as `0ms`.

## Scope

- `_threshold_failures()` now reports unknown timing stages and lists available stage names.
- Added a CLI regression test for an unknown stage threshold.

## TDD Evidence

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q -k "stage_threshold_name_is_unknown"`
  - Failed because the CLI returned `0` for `--max-stage-ms retrieval=80`.
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q -k "stage_threshold_name_is_unknown or thresholds_are_exceeded"`
  - `2 passed, 42 deselected`.
- Related regression: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py -q -k "longform_scale_smoke_cli or longform_scale_smoke_reports or threshold or cleanup"`
  - `10 passed, 34 deselected`.

## Full Verification

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
  - `679 passed in 64.02s`.
- `npm run build` in `frontend`
  - Passed.
- `npm run test:unit -- --run` in `frontend`
  - `64 passed`; `435 passed`.
- `git diff --check`
  - Passed.
- DeepSeek key scan
  - `NO_MATCH`.

## Smoke Verification

- `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 120 --words-per-chapter 800 --target-chapter 60 --cleanup --max-elapsed-ms 30000 --max-stage-ms seed_project=15000 --max-stage-ms memory_rebuild=8000 --max-stage-ms retrieval_reindex=8000 --max-stage-ms context_build=8000`
  - Passed; `elapsed_ms=965`, `retrieval_reindex=701`, `context_build=106`, no future/out-of-range retrieval evidence.
