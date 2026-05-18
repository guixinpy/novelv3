# Longform Scale Phase 71

## Goal

Make the Athena overview maintenance action reliable for thousand-chapter repair backlogs.

## Success Criteria

1. The frontend repair client can pass `repair_limit`.
2. The Athena store repairs longform maintenance in 500-item batches.
3. One user action continues until the backend reports no remaining maintenance issues.
4. Existing repair state still updates diagnostics from the latest backend result.

## Steps

1. Add a failing store test for multi-batch longform maintenance repair.
2. Add `repair_limit` query support to the API client.
3. Loop store repair calls while `has_more` and remaining issues exist.
4. Run the focused store test, full frontend tests, and build.
