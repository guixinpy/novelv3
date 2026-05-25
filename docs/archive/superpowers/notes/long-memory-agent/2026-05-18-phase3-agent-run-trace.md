# Phase 3 Agent Run Trace

## Runtime

- Date: 2026-05-18.
- Verification tier: T1 plus one T2 runtime dogfood run.
- Backend base URL: `http://127.0.0.1:8001`.
- Secret handling: the model API key was used only as a runtime environment variable and was not written to source, docs, or `.env`.
- Local database note: `data/mozhou.db` has an older `alembic_version` value even though later tables already exist. To avoid risky duplicate migrations against dogfood data, this phase created only the new `writing_agent_runs` and `writing_agent_steps` tables with SQLAlchemy `create(checkfirst=True)` for the local runtime. The repository still includes a normal Alembic migration for fresh or properly stamped databases.

## Implementation

- Added persistent Agent orchestration records:
  - `WritingAgentRun`.
  - `WritingAgentStep`.
- Added API routes:
  - `POST /api/v1/projects/{project_id}/agent-runs`.
  - `GET /api/v1/projects/{project_id}/agent-runs`.
  - `GET /api/v1/projects/{project_id}/agent-runs/{run_id}`.
  - `POST /api/v1/projects/{project_id}/agent-runs/{run_id}/cancel`.
- Added a thin execution service that reuses existing action execution paths instead of duplicating setup/storyline/outline/chapter generation.
- Added tool-step recording for:
  - `generate_setup`.
  - `generate_storyline`.
  - `generate_outline`.
  - `generate_chapter`.
- Added chapter generation diagnostics into Agent step output:
  - model-call `trace_id`.
  - chapter target id.
  - chapter index.
  - chapter length decision.
  - Athena/world-model proposal queue diagnostic.

## Dogfood Novel Progress

- Novel: `《雾港回声》`.
- Project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Planned total: 600 chapters.
- Generated chapters: 2.
- Current total generated words: `7246`.

## Agent Run Evidence

- Agent run id: `78894cc3-d7f3-4d4e-8179-e8e461f38954`.
- Status: `success`.
- Goal: generate Chapter 2 through Writing Agent and record length gate plus Athena proposal queue diagnostic.
- Step id: `18d807ee-b630-47d1-8a5e-edbce0e43b26`.
- Tool: `generate_chapter`.
- Step status: `success`.
- Generated target:
  - target type: `chapter`.
  - target id: `ce84128f-bddb-42a9-b5ef-4d9f79e68312`.
  - chapter index: `2`.
- Model trace id: `08fd0a3d-6c2c-4d54-993c-094af134be9b`.

## Chapter 2 Metrics

- Title: `第2章`.
- Word count: `3511`.
- Status: `generated`.
- Trace status: `success`.
- Trace latency: `47567 ms`.
- Prompt tokens: `3622`.
- Completion tokens: `2651`.
- Trace context budget:
  - included blocks: `8`.
  - omitted blocks: `0`.
  - used context chars: `5606`.
  - remaining context chars: `18394`.
- Prose quality trace:
  - status: `prose`.
  - line count: `98`.
  - outline marker count: `0`.
  - sentence ending count: `220`.
  - warnings: none.

Chapter length decision:

```json
{
  "status": "over",
  "decision": "accept_with_warning",
  "actual_word_count": 3511,
  "target_min_word_count": 1700,
  "target_average_word_count": 2000,
  "target_max_word_count": 2300
}
```

Athena/world-model proposal diagnostic:

```json
{
  "status": "missing",
  "profile_version": null,
  "total_items": 0,
  "reason": "missing_profile"
}
```

## Quality Review

Chapter 2 is prose-like正文, not outline output. It continues the fog-port memory anomaly thread, keeps 林深 and 苏晚晴 in an active scene, and introduces concrete sensory detail and investigative pressure.

Quality issues:

- The chapter is still too long for the configured 2000-word average. This is the second consecutive over-target chapter.
- The title is generic `第2章`, which is weaker than a semantic chapter title and should be corrected by generation or post-generation title extraction.
- Athena world-model analysis is skipped because the project has no world-model profile, so new facts are not entering the proposal review queue.

## Maintenance / Memory / World Model

Longform maintenance after Chapter 2:

```json
{
  "status": "current",
  "ready_for_writing": true,
  "issue_count": 0,
  "chapter_count": 2,
  "word_target": {
    "status": "drift",
    "over_target_count": 2,
    "over_target_chapter_indexes": [1, 2]
  },
  "stale_memory_count": 0,
  "missing_memory_count": 0,
  "stale_retrieval_count": 0,
  "missing_retrieval_count": 0
}
```

Retrieval diagnostics after Chapter 2:

```json
{
  "embedding_provider": "local",
  "embedding_model": "hash-bigram-v1",
  "vector_dimension": 96,
  "total_documents": 9,
  "total_chunks": 19,
  "total_terms": 8142,
  "total_embeddings": 19,
  "documents_by_source_type": {
    "chapter": 2,
    "longform_memory": 7
  }
}
```

Longform memory diagnostics after Chapter 2:

```json
{
  "chapter_count": 2,
  "current_word_count": 7246,
  "counts_by_type": {
    "chapter": 2,
    "arc": 2,
    "volume": 2,
    "global": 1
  },
  "total_memories": 7
}
```

## Issues Found

- The existing local dogfood SQLite database has stale Alembic revision metadata. This does not block the phase, but it needs a future database hygiene plan before relying on migrations for long-running local data.
- Both generated chapters are over target length. The Agent now records this, but it does not yet revise, split, or regenerate.
- World-model proposal queue remains unavailable because `profile_version=null`.
- Chapter 2 title is generic instead of semantic.
- Phase 3 still executes a user-specified tool sequence; it does not yet choose tools autonomously from natural-language intent.

## Issues Fixed

- The system now has durable Agent run and Agent step records.
- Tool execution is visible as ordered steps rather than hidden ad hoc API calls.
- Chapter length drift is recorded in the Agent step output.
- Missing Athena/world-model profile state is recorded in the Agent step output.
- The first real dogfood chapter generated through the Agent path is complete.

## Verification

- T1:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q`.
  - Result: `7 passed`.
- T1/T2 focused regression:
  - Command: `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing.py tests\test_chapters.py::test_generate_chapter_records_model_call_trace -q`.
  - Result: `36 passed`.
- Diff hygiene:
  - Command: `git diff --check`.
  - Result: exit code `0`.
- Secret scan:
  - Command: `rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references`.
  - Result: no matches.
- Runtime:
  - Backend health on `8001`: `{"status":"ok"}`.
  - Agent run generated Chapter 2 successfully through `/agent-runs`.

## Next Phase Recommendation

Phase 4 should focus on making Agent preflight and post-generation gates actionable:

- Initialize or import Athena world-model profile for the dogfood project before Chapter 3.
- Add a preflight readiness step to Agent runs that checks outline, previous chapter, longform memory, retrieval, and world-model profile state.
- Convert `accept_with_warning` length decisions into an explicit policy: accept, revise, split, or stop.
- Improve chapter title extraction/generation so chapter titles are semantic.
- Generate Chapter 3 only after the Agent can report preflight readiness and world-model proposal state.
