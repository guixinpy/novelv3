# Phase 120 - Reuse Search Query Tokens

## Goal
Reduce repeated query tokenization during query-aware retrieval context assembly, which runs during longform chapter work.

## Findings
- A single `search_retrieval` call tokenized the same query many times while scoring candidates and building snippets.
- This cost grows with the number of candidate chunks considered for a long project.

## Changes
- `search_retrieval` now tokenizes the cleaned query once.
- Candidate token selection, local query embedding, lexical scoring, and snippet generation reuse the prepared query tokens.
- Search scoring behavior is unchanged: the same lexical overlap, phrase bonus, vector score, and final weighting remain in place.

## Verification
- Added regression coverage proving a search tokenizes the query once.
- Re-ran Athena retrieval tests: `29 passed`.
- Re-ran `1000 x 1000` longform smoke with cleanup:
  - `retrieval_reindex`: `7991 ms`
  - `context_build`: `433 ms`
  - `elapsed_ms`: `8881 ms`
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend pytest suite: `543 passed`.
