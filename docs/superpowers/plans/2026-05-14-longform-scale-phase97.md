# Phase 97 - Collapse Long Storyline Side Branches

## Goal

Keep Athena storyline review usable for long novels by preserving a clear main branch while avoiding automatic rendering of every side-branch milestone.

## Changes

- Large storyline trees now keep main plotlines expanded and auto-collapse non-main branches on first load.
- The auto-collapse decision is initialized only when the plotline data changes, so user toggles remain stable for the current data set.
- Smaller storylines retain the previous default-expanded behavior.

## Verification

- Added a regression test covering a 160-milestone storyline with main and side branches.
- Re-ran the full NarrativeWorkbench test file.
- Re-ran the complete frontend unit suite and production build.
