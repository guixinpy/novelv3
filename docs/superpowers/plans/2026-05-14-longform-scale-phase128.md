# Phase 128 - Avoid Serializing Full Text in Retrieval Source Hashes

## Goal
Keep the expanded retrieval source hash from adding unnecessary CPU and memory work during full reindex.

## Problem
Phase 127 expanded retrieval source hashes to include metadata, but the first implementation placed the full source text inside the JSON payload before hashing. For million-word projects this duplicated large strings through JSON serialization even though the final hash only needs a stable text digest.

## Changes
- `_source_hash` now hashes source text separately with sha256.
- The JSON payload contains `text_sha256` plus source metadata, title, chapter anchor, source ref, and profile version.
- Source metadata changes still affect the final source hash.

## Verification
- Added a regression test proving `_source_hash` does not pass full text into `json.dumps`.
- Re-ran Athena retrieval tests: `36 passed`.
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend suite: `551 passed`.
- Re-ran 1000 chapter / 1,000,000 word smoke: `retrieval_reindex=8247 ms`, `context_build=284 ms`.
