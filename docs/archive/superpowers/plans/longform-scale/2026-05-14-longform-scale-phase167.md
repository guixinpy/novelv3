# Longform Scale Phase 167 - Narrative Atlas Windowed Graph Loading

## Problem

Athena narrative graph still requested the full evolution plan when opening `narrative?view=graph`.
For thousand-chapter projects this makes the graph path a longform-scale weak point even though the canvas can already render a local 80-chapter window.

The existing graph also treated server-windowed plans as small plans because metrics and paging were based only on loaded chapter nodes.

## Change

- Route loader now opens graph view with a bounded evolution-plan window:
  - `chapter_limit=80`
  - `plotline_limit=20`
  - `milestone_limit=500`
  - `foreshadowing_limit=500`
- Narrative atlas detects server-window metadata (`chapters_total`, `chapters_offset`, `chapters_limit`) and shows the current chapter scope.
- Atlas chapter paging emits `loadChapterWindow` for server-backed windows instead of mutating only local state.
- `AthenaView` converts atlas paging into a windowed `loadEvolutionPlan` request with graph relation limits.
- Atlas metrics prefer server total metadata so paged views still show project scale.

## Tests

Red failures confirmed before implementation:

- `athenaSectionLoader` expected graph route to request a windowed plan.
- `NarrativeAtlasView` expected server-window scope and paging event.
- `AthenaView` expected atlas paging to call the windowed evolution-plan API.

Verification after implementation:

- `npm run test:unit -- athenaSectionLoader NarrativeAtlasView AthenaView`
- `npm run test:unit`
- `npx vue-tsc --noEmit`
- `npm run build`

## Result

Graph view no longer uses the full evolution-plan request by default. The current graph path is now aligned with thousand-chapter browsing: it loads a bounded chapter window, preserves total metrics, and can request the next/previous server window.
