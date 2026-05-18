# Phase 239: Window Proposal Review Queue

## Goal

Allow large proposal review queues to be browsed in offset windows instead of exposing only the first limited queue slice.

## RED

- `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py::test_world_model_proposal_review_queue_supports_offset_window -q`
  - Failed because `/world-model/proposal-review-queue` and the Athena facade ignored `offset` and returned no offset metadata.
- `npm run test:unit -- --run src/api/client.worldModel.test.ts`
  - Failed because `getWorldProposalReviewQueue()` ignored queue window params.

## GREEN

- Added `offset` to `build_proposal_review_queue()`, the world-model endpoint, and the Athena facade.
- Added response `offset` metadata and corrected `has_more` to use `offset + returned_items < total_items`.
- Added frontend `ProposalReviewQueueQuery` and query serialization.

## Verification

- Targeted backend and frontend tests pass after implementation.
- Full backend, frontend build, frontend unit tests, whitespace diff check, and key scan are required before commit.
