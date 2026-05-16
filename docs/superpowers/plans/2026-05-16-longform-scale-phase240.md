# Phase 240 - Frontend Proposal Review Queue Pagination

## Goal

Close the frontend loop for the proposal review queue windowing added in the backend.
The setup panel must request a bounded review queue window, show how many proposal
items are currently loaded, and let the user load the next window when the backend
reports more data.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/stores/worldModel.test.ts src/components/athena/ProposalWorkbench.test.ts`
  - Failed because the initial queue request did not pass `{ offset: 0, limit: 200 }`.
  - Failed because `loadMoreProposalReviewQueue()` did not exist.
  - Failed because the proposal workbench did not expose loaded queue progress or a load-more control.
- GREEN:
  - Same targeted command passed with `35 passed`.

## Changes

- Added `PROPOSAL_REVIEW_QUEUE_PAGE_SIZE = 200` to the world model store.
- Normalized review queue metadata from older and newer backend responses.
- Added `loadingMoreProposalReviewQueue` and `loadMoreProposalReviewQueue(projectId)`.
- The proposal workbench now shows loaded item progress and calls the store load-more action.
- Removed the hard-coded first-six-clusters display cap so loaded windows are visible.

## Verification

Full verification is required before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build`
- `npm run test:unit -- --run`
- `git diff --check`
- DeepSeek key scan must return `NO_MATCH`.
