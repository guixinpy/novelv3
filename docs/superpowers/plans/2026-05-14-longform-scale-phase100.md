# Phase 100 - Light Retrieval Diagnostics Counts

## Goal

Keep Athena retrieval diagnostics responsive as long projects accumulate many retrieval documents, chunks, terms, and embeddings.

## Changes

- Retrieval diagnostics totals now use explicit `count(id)` queries for documents, chunks, terms, and embeddings.
- Source-type aggregation and diagnostics response shape are unchanged.

## Verification

- Added SQL-level regression coverage proving diagnostics count queries do not select retrieval metadata, chunk text, chunk metadata, or embedding vectors.
- Re-ran the complete Athena retrieval test file.
- Re-ran the full backend pytest suite.
