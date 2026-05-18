# Longform Scale Phase 168 - Timeline Fallback Windowing

## Problem

When Athena timeline data existed but contained no events, the route loader fetched the full evolution plan to build timeline fallback chapter events.
For long serial novels this makes a mostly empty timeline path load every planned chapter unnecessarily.

## Change

- Timeline fallback now uses the same bounded chapter plan window as the chapters view.
- The fallback request loads:
  - `chapter_limit=50`
  - `plotline_limit=1`
  - `foreshadowing_limit=1`
- Storyline and graph routes keep their own bounded windows.

## Tests

Red failure confirmed before implementation:

- `athenaSectionLoader` still called `loadEvolutionPlan(projectId)` without params for empty timeline fallback.

Verification after implementation:

- `npm run test:unit -- athenaSectionLoader`
- `npm run test:unit`
- `npx vue-tsc --noEmit`
- `npm run build`

## Result

Timeline fallback no longer pulls the full evolution plan by default. Empty or not-yet-generated timeline views now keep initial data loading bounded for thousand-chapter projects.
