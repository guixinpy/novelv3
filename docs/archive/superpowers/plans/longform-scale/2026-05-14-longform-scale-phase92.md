# Phase 92 - Single Chapter Outline Lookup

## Goal

Avoid loading full outline JSON blobs when building chapter-specific prompt context for thousand-chapter projects.

## Changes

- Added `find_outline_chapter` as a shared database-side lookup for one chapter outline item.
- Reused the lookup in:
  - chapter generation target-outline prompt block
  - Athena chapter world context package
  - retrieval context query construction
- Preserved existing prompt output for chapter title, summary, characters, and scenes.

## Verification

- Added regression coverage proving `build_chapter_context_package` keeps the requested chapter outline while not selecting raw `outlines.chapters`, `outlines.plotlines`, or `outlines.foreshadowing` result columns.
- Re-ran affected Athena dialog, chapter generation, retrieval, and longform scale suites.
