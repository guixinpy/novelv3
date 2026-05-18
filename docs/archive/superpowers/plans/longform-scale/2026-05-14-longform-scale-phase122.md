# Phase 122 - Bound Retrieval Candidate Scoring

## Goal
Reduce per-chapter retrieval context latency by limiting the default number of candidate chunks scored for small result limits.

## Changes
- Reduced the default stable fallback candidate pool from `max(limit * 80, 400)` to `max(limit * 40, 240)`.
- Reduced the default indexed lexical candidate pool from `max(limit * 160, 800)` to `max(limit * 80, 480)`.
- Explicit `candidate_limit` still overrides both defaults.

## Rationale
- Query-aware context usually requests a small final result set, commonly `limit=6`.
- Scoring nearly 1000 candidates for 6 final items adds latency on every longform chapter operation.
- Existing lexical index ordering keeps the strongest token matches first before vector and lexical scoring.

## Verification
- Added regression coverage proving default search scoring is bounded to at most `480` candidates for `limit=6`.
- Re-ran Athena retrieval tests: `31 passed`.
- Re-ran retrieval/context/smoke subset from longform scale tests: `17 passed`.
- Re-ran `1000 x 1000` longform smoke with cleanup:
  - `retrieval_reindex`: `8143 ms`
  - `context_build`: `313 ms`
  - `elapsed_ms`: `8904 ms`
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend pytest suite: `545 passed`.
