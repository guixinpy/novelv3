# Phase 95 - Avoid Timeline Plan Preload

## Goal

Keep Athena narrative timeline navigation lightweight on long projects by avoiding full evolution-plan loading when timeline events are already available.

## Changes

- Split narrative timeline and graph loading paths in `createAthenaSectionLoader`.
- Timeline view now loads `timeline` first and only loads the full evolution plan when timeline events are absent, preserving the existing planning fallback.
- Graph, storyline, chapters, and foreshadowing views keep their existing full-plan loading behavior.

## Verification

- Added a regression test proving timeline view does not call `loadEvolutionPlan` when `loadTimeline` returns events.
- Re-ran the full Athena section loader test file.
- Re-ran the complete frontend unit suite and production build.
