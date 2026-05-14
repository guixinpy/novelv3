# Phase 153 - Refresh proposal bundle status by status only

## Goal

Keep proposal review status updates cheap for large Athena world-model bundles.

## Why

Bundle status refresh only needs the set of item statuses. Loading every `WorldProposalItem` row pulls heavy fields such as `notes`, `object_ref_or_value`, and `evidence_refs` into memory on every review/split/rollback path. Large longform projects can accumulate many proposal items per bundle.

## TDD

RED:

- Added a bundle status refresh test with 50 proposal items containing heavy JSON/text fields.
- The test captures SQL and asserts only `world_proposal_items.item_status` is selected from proposal items.
- It failed because the old refresh loaded full ORM rows.

GREEN:

- `_refresh_bundle_status` now queries distinct `item_status` values.
- Existing status derivation behavior is unchanged.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_proposals.py::test_refresh_bundle_status_reads_only_item_status_column -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_proposals.py backend\tests\test_world_frontend_api.py -q` -> 88 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 575 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 11,266 ms, elapsed 12,174 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
