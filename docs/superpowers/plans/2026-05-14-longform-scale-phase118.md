# Phase 118 - Use Core Inserts for Retrieval Reindex Rows

## Goal
Reduce full retrieval reindex write overhead for million-word projects by avoiding SQLAlchemy ORM bulk mapping costs on large retrieval row batches.

## Evidence
- Profiling a `1000 x 1000` longform smoke run showed `reindex_project_retrieval` dominated by retrieval row insertion.
- The largest cumulative costs were SQLAlchemy ORM bulk mapping and SQLite executemany calls for retrieval documents, chunks, terms, and embeddings.

## Changes
- Added a retrieval insert helper that uses SQLAlchemy Core executemany inserts.
- Replaced `bulk_insert_mappings` in retrieval index batch flushing.
- Kept the existing source batch size, chunking, tokenization, embedding, and search behavior unchanged.

## Verification
- Added regression coverage that fails if retrieval reindex still uses ORM `bulk_insert_mappings`.
- Updated batch-write tests to observe the Core insert helper.
- Re-ran focused Core insert tests: `4 passed`.
- Re-ran Athena retrieval tests: `28 passed`.
- Re-ran `1000 x 1000` longform smoke with cleanup:
  - `retrieval_reindex`: `8167 ms`
  - `elapsed_ms`: `9087 ms`
  - `total_documents`: `2061`
  - `total_chunks`: `3061`
  - `total_terms`: `247265`
