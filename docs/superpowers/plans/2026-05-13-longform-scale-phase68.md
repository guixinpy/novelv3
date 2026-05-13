# Longform Scale Phase 68

## Goal

Reduce local retrieval embedding cost by hashing repeated tokens once per chunk.

## Success Criteria

1. Repeated tokens produce the same weighted vector contribution without repeated hash calls.
2. Retrieval indexing remains compatible with the token-batch fast path.
3. Retrieval tests pass.
4. The 1000-chapter longform smoke gate stays under the current retrieval budget.

## Steps

1. Add a failing unit test that counts repeated-token hash calls.
2. Aggregate local embedding tokens with `Counter`.
3. Re-run retrieval tests.
4. Re-run the 1000-chapter smoke gate.
