# Phase 124 - Window Narrative Atlas Construction

## Goal
Reduce frontend graph work for thousand-chapter projects by building the narrative atlas for the active chapter window instead of constructing the full graph first and trimming it afterward.

## Problem
`NarrativeAtlasView` already rendered large plans through an 80-chapter local window, but it still called `buildNarrativeAtlasGraph` without a range. For 1000+ chapter projects this meant all chapter nodes, trunk edges, milestones, foreshadowing nodes, and timeline event anchors were created before display filtering.

## Changes
- Added optional `chapterRange` support to `buildNarrativeAtlasGraph`.
- Filtered chapter spine, milestones, foreshadowing, and timeline events during graph construction when a local window is active.
- Added lightweight chapter index and metric collectors so `NarrativeAtlasView` can keep global counts without building a full graph.
- Kept large atlas rendering scoped to the current 80-chapter window.

## Verification
- Added a regression test that failed before the fix: a 1000-chapter graph with range `401-480` returned all 1000 chapter nodes instead of 80.
- Re-ran targeted graph/view tests: `14 passed`.
- Re-ran the full frontend unit suite: `373 passed`.
- Re-ran frontend build: `vue-tsc --noEmit && vite build` completed successfully.
