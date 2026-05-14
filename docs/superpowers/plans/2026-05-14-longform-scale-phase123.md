# Phase 123 - Roll Back Failed Chapter Side Effects

## Goal
Keep chapter generation stable when non-critical post-generation work fails.

## Problem
Chapter generation intentionally ignores failures from consistency checks, Athena world analysis, and retrieval indexing. Those failures were swallowed without a rollback, which could leave the SQLAlchemy session dirty and interfere with later maintenance steps in the same request.

## Changes
- Added rollback cleanup when the L1 consistency check fails.
- Added rollback cleanup when Athena chapter analysis fails.
- Added rollback cleanup when chapter retrieval indexing fails.
- Chapter generation still returns the generated chapter when these non-critical side effects fail.

## Verification
- Added regression coverage proving retrieval indexing failure triggers rollback without failing chapter generation.
- Re-ran chapter tests: `22 passed`.
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend pytest suite: `546 passed`.
