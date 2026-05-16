# Phase 238: Stable Proposal Bundle Pagination

## Goal

Make proposal bundle pagination deterministic when multiple bundles share the same `updated_at` and `created_at` timestamps, preventing page drift in large review backlogs.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py::test_list_world_proposal_bundles_uses_id_tie_breaker_for_stable_pages -q`
  - Failed because bundles with identical timestamps returned in insertion order instead of a deterministic latest-first id order.

## GREEN

- Added `WorldProposalBundle.id.desc()` as the final order key for `/world-model/proposal-bundles`.
- Existing offset/limit pagination and count behavior remain unchanged.

## Verification

- Targeted backend test passes after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.
