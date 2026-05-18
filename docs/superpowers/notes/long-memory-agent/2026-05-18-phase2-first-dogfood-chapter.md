# Phase 2 First Dogfood Chapter

## Runtime

- Date: 2026-05-18.
- Verification tier: T1/T2.
- Backend base URL used: `http://127.0.0.1:8001`.
- Reason for port change: port `8000` had an unrelated or unidentified listener, so the phase used `8001` instead of stopping an unverified process.
- Model provider: DeepSeek-compatible runtime configuration.
- Secret handling: API key was supplied only through runtime environment. It was not written to docs, `.env`, source code, or commits.

## Project

- Project name: `雾港回声`.
- Project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Genre: `都市悬疑 / 轻科幻 / 群像成长`.
- Target chapter count: `600`.
- Target word count: `1200000`.
- AI model: `deepseek-chat`.
- Purpose: longform dogfood project for validating whether novelv3 can support a conversation-driven, long-memory, tool-orchestrating web-novel writing Agent.

## Generated Artifacts

- Setup generated:
  - id: `38532a88-bc20-4b13-8a0c-00ac0f006590`.
  - status: `generated`.
- Storyline generated:
  - id: `63694c94-7dd0-4e0b-be60-697bf87436be`.
  - status: `generated`.
- Outline generated:
  - id: `49229388-f2d6-4bdb-bfa0-f4e8b9aa0beb`.
  - status: `generated`.
  - total chapters: `600`.
  - chapter 1 title: `雾中回声`.
- Chapter 1 generated:
  - title: `雾中回声`.
  - status: `generated`.
  - word count: `3735`.
  - trace id: `febf0ad4-eadd-4b26-b97a-76f6d54468f9`.

## Chapter 1 Metrics

- Target minimum word count: `1700`.
- Target average word count: `2000`.
- Target maximum word count: `2300`.
- Actual word count: `3735`.
- Trace word-target status: `over`.
- Deviation from average: `+1735`.
- Prose quality trace:
  - status: `prose`.
  - line count: `103`.
  - outline marker count: `0`.
  - sentence ending count: `204`.
  - warnings: none.

## Quality Review

Chapter 1 is usable as prose and not an outline-style response. It opens with a concrete fog-port scene, introduces the memory anomaly, gives the protagonist an active investigation path, and closes with a forward hook.

The main quality concern is length control. The chapter meets the 2000+ target, but it overshoots the configured average and max range. For long-term 600-chapter generation, this is not immediately harmful, but it means the Agent needs a chapter-length control loop rather than a one-shot prompt.

## Maintenance / Memory / World Model

Retrieval diagnostics after chapter generation:

```json
{
  "embedding_provider": "local",
  "embedding_model": "hash-bigram-v1",
  "vector_dimension": 96,
  "total_documents": 5,
  "total_chunks": 10,
  "total_terms": 4209,
  "total_embeddings": 10,
  "documents_by_source_type": {
    "chapter": 1,
    "longform_memory": 4
  }
}
```

Longform memory diagnostics after chapter generation:

```json
{
  "chapter_count": 1,
  "current_word_count": 3735,
  "counts_by_type": {
    "chapter": 1,
    "arc": 1,
    "volume": 1,
    "global": 1
  },
  "total_memories": 4
}
```

Maintenance diagnostics:

```json
{
  "status": "current",
  "ready_for_writing": true,
  "issue_count": 0,
  "word_target": {
    "status": "drift",
    "under_target_count": 0,
    "within_target_count": 0,
    "over_target_count": 1,
    "over_target_chapter_indexes": [1]
  },
  "stale_memory_count": 0,
  "missing_memory_count": 0,
  "stale_retrieval_count": 0,
  "missing_retrieval_count": 0
}
```

Athena proposal review queue:

```json
{
  "profile_version": null,
  "total_items": 0,
  "returned_items": 0,
  "clusters": []
}
```

This suggests either chapter generation does not currently emit visible world-model proposals, or the dogfood project does not yet have the Athena profile state needed for proposal clustering.

## Issues Found

- `outline/generate` could fail with a 500 response when the model returned structured scene objects instead of `list[str]`. This is a product issue because LLMs often return richer scene data than the strict schema allowed.
- Chapter generation exceeded the target average/max word range. This should become an Agent-level control loop later.
- Athena proposal review queue remained empty after setup, storyline, outline, and chapter generation. This needs investigation before world-model assisted longform writing can be trusted.
- The Phase 2 plan initially used `model-traces`; the actual endpoint is `model-call-traces`.
- The Phase 2 plan initially used a `$pid` PowerShell variable. `$PID` is read-only in PowerShell, so project id variables should use `$projectId`.
- The Phase 2 plan initially guessed `world/proposals`; the useful existing endpoint for proposal review inspection is `athena/evolution/proposal-review-queue`.

## Issues Fixed

- Added outline chapter normalization in `backend/app/api/outlines.py`.
- Added schema-side defensive normalization in `backend/app/schemas/outline.py`.
- Added regression coverage in `backend/tests/test_outlines.py` for structured `scenes` and structured `characters`.
- Regenerated the outline successfully after the fix and then generated chapter 1 through the real backend path.

## Verification

- T1 regression:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_outlines.py::test_generate_outline_normalizes_structured_scene_items -q`
  - Result observed during Phase 2: passed.
- T1 outline test file:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_outlines.py -q`
  - Result observed during Phase 2: `13 passed`.
- T2 runtime dogfood:
  - Created project `雾港回声`.
  - Generated setup, storyline, outline, and chapter 1 through backend API.
  - Inspected generation trace, retrieval diagnostics, longform memory diagnostics, maintenance diagnostics, and Athena proposal review queue.

## Next Phase Recommendation

Phase 3 should focus on the first Agent-core slice instead of adding more ad hoc generation endpoints:

- Add a lightweight Writing Agent run model that records a user goal, selected tools, steps, outputs, and trace links.
- Treat existing project/setup/storyline/outline/chapter APIs as tools that the Agent can call.
- Add a chapter-length control policy that can detect over/under target output and decide whether to accept, revise, or split content.
- Investigate why Athena proposal review queue is empty after chapter generation.
- Generate chapter 2 through the Agent run path once the first tool-orchestration trace exists.
