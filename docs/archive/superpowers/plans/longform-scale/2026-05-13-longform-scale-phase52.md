# Longform Scale Phase 52

## Goal

Reduce full retrieval reindex time by removing per-token ORM `add()` calls during lexical term indexing.

## Success Criteria

1. Lexical terms are still indexed and counted.
2. Search behavior remains covered by existing retrieval tests.
3. Reindex no longer calls `Session.add()` once per `RetrievalTerm`.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that counts `Session.add()` calls for `RetrievalTerm`.
2. Replace per-token `add()` with batch insertion for chunk terms.
3. Run retrieval tests, full verification, and a 1000-chapter smoke timing check.
