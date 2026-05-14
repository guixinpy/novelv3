# Phase 93 - Bound Post Generation Outline Reads

## Goal

Prevent chapter generation completion from loading full outline JSON for title extraction and single-chapter longform memory refresh.

## Changes

- Chapter generation now uses `find_outline_chapter` to derive the generated chapter title from only the target chapter outline item.
- `refresh_longform_memory_for_chapter` now uses the same single-chapter outline lookup instead of building a full outline lookup map.
- Full longform memory rebuild still keeps the full outline lookup because that path intentionally rebuilds every chapter memory.

## Verification

- Added a generation-path regression test covering a 1000-chapter outline and asserting no raw `outlines.chapters`, `outlines.plotlines`, or `outlines.foreshadowing` result columns are selected.
- Re-ran chapter generation, longform scale, and Athena retrieval suites.
