# Longform Scale Phase 64

## Goal

Turn the longform scale smoke script into an enforceable performance gate with explicit failure thresholds.

## Success Criteria

1. `scripts/longform_scale_smoke.py` accepts `--max-elapsed-ms`.
2. It accepts repeated `--max-stage-ms stage=value` thresholds.
3. The script prints the full report and returns nonzero when any threshold is exceeded.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a failing CLI unit test using a fake smoke report.
2. Add threshold parsing and validation helpers.
3. Wire threshold failures into `main`.
4. Run targeted tests, a small CLI command check, then full verification.
