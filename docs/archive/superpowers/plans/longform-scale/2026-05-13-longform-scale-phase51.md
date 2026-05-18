# Longform Scale Phase 51

## Goal

Make the longform scale smoke report actionable by recording stage-level timings.

## Success Criteria

1. Smoke reports timing for seed, task progress, memory rebuild, retrieval reindex, context build, and task completion.
2. Timing values are non-negative integers.
3. Existing memory, retrieval, context, and task assertions continue to pass.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test for `timings_ms`.
2. Instrument `run_longform_scale_smoke` around each major stage.
3. Run targeted and full verification.
