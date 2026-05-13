# Longform Scale Phase 65

## Goal

Keep Athena chapter-plan search responsive when a long novel has hundreds or thousands of planned chapters.

## Success Criteria

1. Common chapter searches do not render every matching chapter card.
2. Users can see how many matches are currently shown versus total matches.
3. Existing chapter windowing and jump behavior remains unchanged.
4. Component tests pass before commit.

## Steps

1. Add a failing frontend test for a broad search over a long chapter plan.
2. Cap rendered search results to a bounded window.
3. Update the range label to show visible and total matches when truncated.
4. Run the focused component test suite.
