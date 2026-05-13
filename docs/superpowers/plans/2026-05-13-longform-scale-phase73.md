# Longform Scale Phase 73

## Goal

Avoid full world-projection work when proposal detail conflict detection only needs chapter-scoped checks.

## Success Criteria

1. Chapter-scoped proposal facts such as `presence_count` do not trigger full current-truth projection construction.
2. Existing chapter-scoped conflict behavior remains unchanged.
3. Non-chapter-scoped truth candidates can still use full projection facts for conflict detection.
4. Backend tests continue to pass.

## Steps

1. Add a failing API test proving chapter-scoped proposal details should not call full projection building.
2. Filter actionable truth items before deciding whether full projection facts are needed.
3. Keep high-impact conflict detection based on actionable item ids.
4. Run the focused API test, full world frontend API tests, backend pytest, diff check, and secret scan.
