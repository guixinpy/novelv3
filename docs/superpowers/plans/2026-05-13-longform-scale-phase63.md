# Longform Scale Phase 63

## Goal

Reduce duplicate retrieval work during longform context construction when the explicit user query already fills the retrieval limit.

## Success Criteria

1. Query-aware retrieval returns user-query results directly when they satisfy `limit`.
2. Context-query retrieval still runs when user-query results are absent or insufficient.
3. Existing source explanation behavior remains unchanged.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that counts retrieval calls for a full user-query result set.
2. Add a short-circuit after user-query retrieval in `_query_aware_result_items`.
3. Run targeted retrieval and longform context tests, a 1000-chapter smoke timing check, then full verification.
