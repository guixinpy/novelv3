# Phase 119 - Retune Retrieval Write Batch Size

## Goal
Retune retrieval write batching after Phase 118 changed the insertion path from ORM bulk mappings to SQLAlchemy Core executemany.

## Findings
- The previous `200` source batch produced `retrieval_reindex` around `8167 ms` after Core inserts.
- `500` source batches regressed to `8416 ms`.
- `50` source batches regressed heavily to `14094 ms`.
- `150` source batches measured `8186 ms`, close to the `200` baseline.
- `100` source batches measured best in repeated smoke runs:
  - first run: `7927 ms`
  - confirmation run: `7863 ms`

## Changes
- Changed `INDEX_WRITE_BATCH_SOURCES` from `200` to `100`.
- Updated the retrieval batching regression test to assert batches follow the configured threshold instead of hard-coding the previous two-batch expectation.

## Verification
- Re-ran the focused batching test after the final value: `1 passed`.
- Re-ran Athena retrieval tests: `28 passed`.
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend pytest suite: `542 passed`.
