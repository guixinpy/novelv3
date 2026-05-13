# Longform Scale Phase 57

## Goal

Reduce retrieval term-table growth for Chinese longform text by indexing higher-signal CJK trigrams instead of both bigrams and trigrams.

## Success Criteria

1. CJK chunks with trigram terms do not also store CJK bigram terms.
2. Long Chinese queries still retrieve matching chapters through indexed trigrams.
3. Short two-character queries can still fall back to text matching when no indexed lexical rows exist.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that checks stored CJK terms and retrieval result.
2. Add an `_indexable_retrieval_terms` filter used only for term-table storage.
3. Keep query tokenization and lexical scoring unchanged.
4. Run targeted tests, full verification, and a 1000-chapter smoke timing check.
