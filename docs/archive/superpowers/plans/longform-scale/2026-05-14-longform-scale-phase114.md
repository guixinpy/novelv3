# Phase 114 - Deterministic Retrieval Term IDs

## Goal
Reduce retrieval reindex CPU overhead for million-word projects by removing per-term UUID generation.

## Changes
- Retrieval term ids are now deterministic within each chunk: `{chunk_id}:term:{term_index}`.
- Retrieval search behavior, token rows, chunk rows, embedding rows, and diagnostics counts are unchanged.

## Verification
- Added a regression test proving reindex no longer calls `uuid4()` for each retrieval term.
- Re-ran Athena retrieval tests: `27 passed`.
- Re-ran million-word smoke:
  - Command: `.\backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
  - Retrieval reindex timing: `8496 ms`, down from Phase 113 `12396 ms`.
  - Total elapsed: `9399 ms`, down from Phase 113 `13328 ms`.
- Re-ran the full backend pytest suite: `538 passed`.
