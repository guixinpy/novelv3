# Phase 96 - Bound Chapter Jump Options

## Goal

Keep Athena chapter planning controls responsive for thousand-chapter projects by avoiding a full chapter option list in the jump selector.

## Changes

- The chapter jump selector now shows only chapters in the active 100-chapter volume.
- When a chapter search is active, the jump selector follows the bounded search result window.
- Empty select values no longer parse as chapter `0`, preventing invalid negative chapter windows.

## Verification

- Added a regression test proving long plans do not render every chapter as a jump option.
- Updated long-plan navigation coverage to use the volume selector before jumping across volumes.
- Re-ran the full NarrativeWorkbench test file, complete frontend unit suite, and production build.
