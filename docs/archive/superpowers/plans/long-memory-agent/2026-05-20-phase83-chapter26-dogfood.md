# Phase83 Plan: Chapter 26 Dogfood

## Phase Goal

Resume the real `《雾港回声》` dogfood loop after Phase81/82 improved high-value world-model proposal handling.

## Novel Work

Target: Chapter 26.

User input should remain low-detail:

```text
继续写下一章
```

Expected Agent behavior:

- detect missing Chapter 26 outline;
- expand the outline window;
- inspect Knowledge Base, longform memory, world model, and job queue;
- pass preflight;
- generate Chapter 26;
- review quality and continuity;
- analyze world-model proposals;
- handle proposal pressure with low-risk and high-value tools when safe.

## System Capability Under Test

- Whether Phase82 cleared Chapter 25 high-value proposal pressure enough to continue.
- Whether the Agent can continue after `identifier_semantic_drift` warnings without hard-blocking generation.
- Whether Chapter 26 preserves the clue pressure around `G-07`, `E-0047`, `EV-2045-0812-07`, Lin Shen's iris anomaly, and `清道夫`.

## Verification Level

T2 dogfood generation.

Planned checks:

- pre-generation route inspection;
- real Agent auto-plan generation;
- quality and continuity review;
- forbidden/drift scan;
- world-model proposal pressure and guarded resolution when appropriate;
- longform memory and retrieval diagnostics.

## Not Doing

- No detailed manual chapter prompt.
- No frontend validation unless frontend files change.
- No broad refactor unless a concrete blocker appears.
- No API key written to disk.
