# Longform Scale Phase 55

## Goal

Prevent proposal review queue endpoints from loading every pending item on large longform projects.

## Success Criteria

1. Review queue accepts a bounded `limit` query parameter.
2. The response reports `total_items`, `returned_items`, `limit`, and `has_more`.
3. World-model and Athena proxy endpoints return the same limited queue.
4. Existing risk clustering and prioritization behavior remains intact.
5. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add an API regression test for a five-item queue with `limit=2`.
2. Add limit handling to the review queue builder and both endpoints.
3. Update schemas and frontend API types.
4. Run targeted and full verification.
