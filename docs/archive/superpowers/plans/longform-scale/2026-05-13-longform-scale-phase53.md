# Longform Scale Phase 53

## Goal

Reduce retrieval indexing CPU work by tokenizing each chunk once for lexical metadata.

## Success Criteria

1. Each indexed chunk is tokenized once in the retrieval indexing path for lexical term generation.
2. Token count and lexical terms remain unchanged.
3. Existing retrieval search tests continue to pass.
4. Full backend, frontend, typecheck, build, diff, and secret checks pass before commit.

## Steps

1. Add a regression test that counts retrieval tokenization calls.
2. Reuse the token list for both `token_count` and term insertion.
3. Run targeted and full verification.
