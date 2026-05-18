# Phase 126 - Window Long Foreshadowing Lists

## Goal
Keep the foreshadowing view responsive when long novels accumulate hundreds of planted and resolved hints.

## Problem
`NarrativeWorkbench` rendered every foreshadowing item at once. For million-word projects, a dense mystery or serial plot can create hundreds of foreshadowing records, which makes the list harder to scan and increases DOM size.

## Changes
- Added a 100-item window for the foreshadowing view.
- Added previous/next controls and a visible range label for large foreshadowing lists.
- Reset/clamped the active foreshadowing window when the source data changes.
- Kept small foreshadowing lists unchanged.

## Verification
- Added a regression test that failed before the fix: a 250-item foreshadowing list rendered all 250 records.
- Re-ran `NarrativeWorkbench` tests: `13 passed`.
- Re-ran the full frontend unit suite: `375 passed`.
- Re-ran frontend build: `vue-tsc --noEmit && vite build` completed successfully.
