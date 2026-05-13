# Longform Scale Phase 74

## Goal

Keep proposal detail payloads small when repeated review actions create many historical impact snapshots.

## Success Criteria

1. Proposal detail returns only the latest impact snapshot.
2. The latest snapshot remains available at `impact_snapshots[0]`, matching current frontend usage.
3. Existing proposal detail and review tests continue to pass.
4. Backend full test suite remains green.

## Steps

1. Add a failing API test for a bundle with three accumulated impact snapshots.
2. Limit the proposal detail impact snapshot query to the latest row.
3. Run the focused API test, full world frontend API tests, backend pytest, diff check, and secret scan.
