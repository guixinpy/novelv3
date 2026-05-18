# Phase 125 - Window Long Storyline Branches

## Goal
Keep the textual storyline view usable when a long-running novel has hundreds of milestones on the main branch.

## Problem
The storyline view automatically collapsed side branches for large plans, but the main branch stayed expanded. A 1000-chapter project can easily produce hundreds of main milestones, which meant the view could still render a very large list at once.

## Changes
- Added an 80-milestone window for expanded storyline branches.
- Added previous/next controls and a visible range label for long branches.
- Reset milestone windows when the storyline data changes.
- Kept existing behavior for small branches and collapsed side branches.

## Verification
- Added a regression test that failed before the fix: a 250-node main branch rendered all 250 milestones.
- Re-ran `NarrativeWorkbench` tests: `12 passed`.
- Re-ran the full frontend unit suite: `374 passed`.
- Re-ran frontend build: `vue-tsc --noEmit && vite build` completed successfully.
