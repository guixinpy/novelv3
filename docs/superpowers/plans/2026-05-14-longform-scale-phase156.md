# Phase 156 - Add windowed narrative plan endpoint mode

## Goal

Provide a backend foundation for loading Athena narrative plan text views without transferring the full chapter/storyline/foreshadowing JSON payload.

## Why

The graph view still needs a full plan, but ordinary narrative text views can be paged. A 1,000+ chapter outline should not require returning every chapter and every foreshadowing item just to display a bounded list.

## TDD

RED:

- Added an `evolution/plan?mode=window` test with 1,000 outline chapters, 60 storylines, and 300 foreshadowing items.
- The test asserts the endpoint returns requested windows and total/has-more metadata.
- It also captures SQL and rejects selecting full `outlines.chapters`, `outlines.plotlines`, `storylines.plotlines`, or `storylines.foreshadowing` JSON columns.
- It failed because the old endpoint ignored `mode=window` and returned full arrays.

GREEN:

- Added explicit `mode=window` query support while preserving default `mode=full` behavior.
- Window mode reads counts through `json_array_length` and item slices through `json_each`.
- Response includes per-list totals, offsets, limits, and `has_more` flags.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py::test_evolution_plan_window_mode_does_not_select_full_plan_json -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_evolution_plan.py backend\tests\test_athena_longform.py backend\tests\test_athena_dialog.py -q` -> 35 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 578 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 12,226 ms, elapsed 13,136 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
