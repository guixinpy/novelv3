# Phase 91 - Bound Prompt Narrative Context

## Goal

Reduce longform prompt-context overhead for thousand-chapter projects by avoiding Python-side loading of large narrative JSON blobs during common generation/dialog paths.

## Changes

- Athena dialog narrative planning summary now projects only:
  - setup id and core concept
  - outline id, total chapter count, chapter JSON count, foreshadowing JSON count
  - storyline id, plotline count, foreshadowing count, and the first five plotline previews
- Chapter generation target-outline context now extracts the requested chapter with SQLite `json_each`, returning only the matching chapter JSON fragment.

## Verification

- Added SQL-level regression coverage to prevent selecting raw large Setup, Outline, and Storyline JSON columns in prompt-context builders.
- Added chapter prompt coverage to ensure single-chapter outline extraction keeps the prompt behavior while avoiding full outline JSON result loading.
