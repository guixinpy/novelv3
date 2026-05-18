# Longform Scale Phase 320 - Refresh Stability Documentation

## Goal

Keep the long-term stability documentation aligned with the current longform smoke gates.

## Finding

`docs/stability-mechanisms.md` did not mention the new writing diagnostics gates, and it still described `docs/` as a nested Git repository. That would mislead future maintenance.

## Change

- Documented `scripts/longform_scale_smoke.py` as the longform scale gate.
- Added the performance and writing quality threshold flags.
- Documented `writing_worker.generation_diagnostics`.
- Replaced the outdated nested-docs warning with a current limitation: synthetic smoke does not replace real long-cycle dogfood.

## Verification

- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
