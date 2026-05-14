# Phase 127 - Make Retrieval Reindex Maintenance No-op Cheap

## Goal
Keep retrieval maintenance cheap when a long project already has a current retrieval index.

## Problem
Repeated project reindexing still did unnecessary work on the preserved-document path:
- Existing retrieval document scans loaded fields that are not needed to decide whether a source can be preserved.
- First-time reindexing scanned chunk/embedding readiness even when no retrieval documents existed.
- Preserved documents were written back with `UPDATE retrieval_documents` even when the source was unchanged.
- Source metadata changes such as chapter title changes were not part of the preservation hash.

## Changes
- Existing retrieval document scans now load only `id`, `source_type`, `source_id`, and `content_hash`.
- First-time reindexing skips embedding-readiness aggregation when there are no existing documents.
- Retrieval source hashes now include text plus source metadata, title, chapter anchor, source ref, and profile version.
- Unchanged preserved documents are skipped without update statements.
- Metadata/title changes now rebuild only the affected retrieval document instead of silently preserving stale metadata.

## Verification
- Added regressions for existing-document projection, first-time readiness skip, unchanged no-op reindex, and metadata-change rebuild.
- Re-ran Athena retrieval tests: `35 passed`.
- Re-ran longform scale tests: `34 passed`.
- Re-ran the full backend suite: `550 passed`.
- Re-ran 1000 chapter / 1,000,000 word smoke: `retrieval_reindex=8376 ms`, `context_build=281 ms`.
- Verified second reindex on the same 1000 chapter project: `second_reindex_ms=142`, `preserved_documents=2061`, `indexed=0`, `removed_documents=0`.
