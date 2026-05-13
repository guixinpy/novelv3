# Longform Scale Phase 72

## Goal

Keep the Athena proposal detail panel responsive when a longform project produces large world-model candidate bundles.

## Success Criteria

1. A selected proposal bundle with many items does not render every item card at once.
2. The detail panel initially renders a bounded item window of 100 cards.
3. The user can explicitly expand the next batch through a visible "show more" control.
4. Switching the selected bundle resets the visible item window.

## Steps

1. Add a failing `ProposalWorkbench` test for a 150-item bundle.
2. Add a fixed-size detail item window and "show more" action.
3. Reset the window whenever the selected bundle changes.
4. Run focused component tests, full frontend unit tests, build, diff check, and secret scan.
