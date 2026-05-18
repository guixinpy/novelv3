# Phase 174 - Refresh Stale Athena Chapter Candidates

## Problem

When a generated chapter was rewritten before review, Athena reused deterministic
chapter-analysis claim ids and skipped matching pending proposal items as duplicates.
That could leave stale pending candidates in the review queue, so approving them would
merge facts from an older chapter version.

## Change

- Kept confirmed truth claims as hard duplicates.
- Reused existing actionable Athena analyzer candidates for the same profile and
  claim id.
- Refreshed changed candidate payloads in place and marked them as `needs_edit`.
- Recalculated impact scopes for bundles whose existing candidates changed.
- Returned `updated.proposal_items` from the chapter analysis endpoint.

## Tests

- RED: `backend/tests/test_athena_longform.py::test_analyze_chapter_refreshes_stale_pending_candidates_after_chapter_rewrite`
- GREEN: target stale-candidate test
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_athena_longform.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Chapter rewrites now refresh still-actionable Athena review candidates instead of
silently preserving stale extracted facts.
