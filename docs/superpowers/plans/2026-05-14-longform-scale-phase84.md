# Longform Scale Phase 84: Bounded Maintenance Repair

## Goal

Prevent longform maintenance repair from turning a large missing-memory backlog into an implicit full memory rebuild. For thousand-chapter projects, repair actions must stay bounded by `repair_limit` so the UI/API can advance in safe batches.

## Change

- Added a regression test for a 60-chapter missing-memory backlog.
- Changed `repair_longform_maintenance` to always refresh only the selected `repair_limit` chapter window.
- Removed the implicit `LARGE_MAINTENANCE_REBUILD_THRESHOLD` branch and unused all-memory id scan.
- Kept explicit full rebuild behavior available through `rebuild_longform_memory` / the rebuild API.

## Verification

- Red: `python -m pytest backend/tests/test_longform_scale.py -k "large_missing_memory_backlog" -q --basetemp .tmp/pytest`
- Green: `python -m pytest backend/tests/test_longform_scale.py -k "large_missing_memory_backlog" -q --basetemp .tmp/pytest`
- Scale suite: `python -m pytest backend/tests/test_longform_scale.py -q --basetemp .tmp/pytest`
