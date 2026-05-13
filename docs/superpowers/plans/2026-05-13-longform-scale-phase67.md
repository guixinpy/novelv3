# Longform Scale Phase 67

## Goal

Avoid duplicate tokenization when building local retrieval embeddings during longform reindexing.

## Success Criteria

1. Local embedding providers can embed pre-tokenized chunks.
2. Retrieval indexing passes token batches to providers that support the fast path.
3. Remote or generic embedding providers still use `embed_texts`.
4. Retrieval tests and a 1000-chapter smoke gate pass before commit.

## Steps

1. Add a failing retrieval test that rejects duplicate text embedding for a token-batch-capable local provider.
2. Add `embed_token_batches` to the local hash embedding provider.
3. Carry chunk tokens through pending embedding rows.
4. Use the token-batch fast path when available.
5. Run retrieval tests and the longform smoke gate.
