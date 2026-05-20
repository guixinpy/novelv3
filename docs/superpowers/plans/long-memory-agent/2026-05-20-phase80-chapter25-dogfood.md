# Phase80 Plan: Chapter 25 Dogfood

## Phase Goal

Continue the real `《雾港回声》` dogfood loop to Chapter 25 after Phase79 added controlled Knowledge Base candidate prompt injection.

## Novel Work

Target: Chapter 25.

Input should remain low-detail:

```text
继续写下一章
```

Expected Agent behavior:

- detect whether Chapter 25 outline is missing;
- expand the outline if needed;
- read Knowledge Base candidates, longform memory, world model, and preflight;
- generate Chapter 25;
- review quality and continuity;
- analyze world-model proposals;
- resolve low-risk proposal pressure when safe.

## System Capability Under Test

- Whether `knowledge_base_candidates` enters chapter generation context.
- Whether a prompt-safe writing pattern affects chapter ending pressure without over-constraining the story.
- Whether the Agent can continue from Chapter 24 with minimal user detail.

## Verification Level

T2 dogfood generation.

Planned checks:

- pre-generation route inspection;
- real Agent auto-plan generation;
- quality and continuity review;
- forbidden/drift scan;
- world-model proposal pressure and guarded resolution if applicable;
- longform memory and retrieval diagnostics.

## Not Doing

- No manual detailed chapter prompt.
- No broad code refactor unless a concrete dogfood blocker appears.
- No frontend validation unless frontend code changes.
- No API key written to disk.
