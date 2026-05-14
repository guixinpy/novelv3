# Phase 121 - Project Retrieval Search Candidate Rows

## Goal
Reduce ORM row hydration and payload size during retrieval search candidate scoring for long projects.

## Changes
- Candidate search rows now use `load_only` for the fields needed by scoring and display.
- `RetrievalChunk` candidates load only id, chunk index, and text.
- `RetrievalDocument` candidates load only id, source fields, title, chapter index, and metadata.
- `RetrievalEmbedding` candidates load only id and vector.

## Notes
- This is primarily a payload and memory-area optimization.
- The `1000 x 1000` smoke run after the change measured `context_build` at `462 ms`, so this phase is not claimed as a speed improvement.

## Verification
- Added SQL-level regression coverage proving candidate selects do not include unused retrieval row columns.
- Re-ran Athena retrieval tests: `30 passed`.
- Re-ran `1000 x 1000` longform smoke with cleanup:
  - `retrieval_reindex`: `8062 ms`
  - `context_build`: `462 ms`
  - `elapsed_ms`: `8975 ms`
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend pytest suite: `544 passed`.
