# Phase 117 - Deduplicate Impact Scope Truth Lookups

## Goal
Keep proposal impact-scope calculation responsive when a longform project produces many candidate facts for the same world-model scope.

## Changes
- Impact-scope truth lookups now run once per unique `(subject_ref, predicate, chapter_scope)` key.
- Chapter-scoped predicates such as `presence_count` still isolate existing truth by chapter.
- Snapshot content and review behavior are unchanged.

## Verification
- Added SQL-level regression coverage proving five duplicate candidate scopes trigger one truth-claim lookup.
- Re-ran impact-scope focused tests.
- Re-ran world proposal tests: `54 passed`.
- Re-ran world frontend API tests: `33 passed`.
- Re-ran the full backend pytest suite: `541 passed`.
