# Phase 154 - Project truth claim lookup narrowly

## Goal

Reduce heavy row loading during world-model conflict detection.

## Why

Proposal bundle detail can detect conflicts against current truth facts. When it needs the existing claim id for a known subject/predicate/value, the lookup only needs `id` and `object_ref_or_value`, but the old query loaded full `WorldFactClaim` rows including heavy notes and evidence JSON.

## TDD

RED:

- Added a truth-claim lookup test with 20 matching subject/predicate facts carrying heavy notes.
- The test captures SQL and asserts only `id` and `object_ref_or_value` are selected from `world_fact_claims`.
- It failed because the old query selected full ORM rows.

GREEN:

- `_find_current_truth_claim_id` now projects only `WorldFactClaim.id` and `WorldFactClaim.object_ref_or_value`.
- Existing Python-side JSON/value comparison behavior is preserved.

## Verification

- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py::test_find_current_truth_claim_id_projects_only_id_and_value -q` -> 1 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py backend\tests\test_world_proposals.py -q` -> 89 passed
- `.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> 576 passed
- `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup` -> passed, retrieval reindex 12,893 ms, elapsed 13,829 ms
- `git diff --check` -> passed
- Exact DeepSeek key scan -> no matches
