# Longform Scale Phase 49

## Goal

Prevent Athena longform maintenance repair from doing unbounded work in one HTTP request.

## Success Criteria

1. Repair accepts a bounded `repair_limit`.
2. A large stale or missing backlog is repaired in repeatable batches.
3. The response exposes whether more work remains.
4. Existing small-project repair behavior still completes in one call.
5. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that repairs only two chapters from a five-chapter backlog.
2. Add `repair_limit` to the repair service and endpoint.
3. Add response fields for `has_more` and `remaining_issue_count`.
4. Update frontend API types and repair tests.
5. Run targeted and full verification.
