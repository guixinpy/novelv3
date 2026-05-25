# Phase69 Report: Chapter Generate Agent Entrypoint

## Summary

Phase69 migrates the direct chapter generation API into the Agent Service control plane.

`POST /api/v1/projects/{project_id}/chapters/{chapter_index}/generate` now creates and executes a `WritingAgentRun(entrypoint="chapter_generate")` with tool `generate_chapter`. The low-level `create_or_replace_chapter()` implementation remains unchanged and continues to handle prompt construction, writing state, traces, consistency checks, Athena analysis, retrieval indexing, and longform memory maintenance.

This is a core step toward longform stability because direct chapter generation is the base path that continuous writing and future batch workflows depend on.

## Reference Assimilation

Adopted:

- `openclaw`: direct API actions should enter the same control-plane abstraction as user-facing intents.
- `hermes-agent`: creative generation should persist durable run and step records.
- `openhuman`: return compact user-facing output while keeping tool execution provenance inspectable.

Not adopted:

- continuous writing start/resume migration;
- prompt changes;
- task queue progress changes;
- frontend Agent run display.

## Changes

- Updated `backend/app/api/chapters.py`.
- Updated `backend/app/schemas/chapter.py`.
- Updated `backend/tests/test_chapters.py`.
- Direct chapter generation now routes through `execute_agent_api_tool()`.
- Chapter responses keep existing fields and add:
  - `agent_run_id`;
  - `control_plane`.
- Existing low-level generation remains in `create_or_replace_chapter()`.
- Model failures now return HTTP 500 through the API while preserving failed Agent run/step and failed trace records.
- Empty normalized chapter output still returns HTTP 502, preserving prior endpoint behavior.
- `last_generation_trace_id: null` remains present when trace success marking fails, preserving prior response shape.

## Control Plane Contract

Entrypoint:

- `chapter_generate`

Control plane version:

- `phase69.chapter_agent.v1`

Tool:

- `generate_chapter`

Tool params:

```json
{
  "chapter_index": 1
}
```

Response metadata:

```json
{
  "agent_run_id": "<run-id>",
  "control_plane": {
    "version": "phase69.chapter_agent.v1",
    "source": "chapter_generate",
    "action_type": "generate_chapter",
    "chapter_index": 1
  }
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py -q -k "test_generate_chapter or agent_entrypoint"
```

Result before implementation: `1 failed, 25 passed, 12 deselected`; failure confirmed no `WritingAgentRun` existed for direct chapter generation.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py -q -k "test_generate_chapter or agent_entrypoint"
```

Result: `26 passed, 12 deselected in 3.57s`.

T1/T2 related backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py tests\test_athena_ontology_agent.py tests\test_athena_evolution_generation_windows.py -q
```

Result: `226 passed in 24.34s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This phase changes the execution path that future real longform generation will use, so later dogfood generation can produce chapters through Agent run records instead of scattered module calls.

## Discovered Issues

- Direct chapter generation still bypassed `WritingAgentRun`.
- Some tests encoded the old behavior where model exceptions escaped through TestClient.
- `response_model_exclude_none=True` would have removed `last_generation_trace_id: null`; this was avoided to preserve response compatibility.

## Fixed Issues

- Direct chapter generation now creates a durable Agent run and step.
- Chapter response includes Agent provenance.
- Failed model calls now leave both failed trace and failed Agent run/step evidence.
- Empty output status remains HTTP 502.
- Existing chapter trace and maintenance behavior remains in the low-level generator.

## Remaining Boundary

Continuous writing remains the largest generation bypass:

- `/writing/start`
- `/writing/resume`
- `/writing/chapters/{chapter_index}/retry`
- range/background generation tasks

Next phase should migrate continuous writing task creation/execution so long-running chapter production also creates Agent runs and remains observable, recoverable, and inspectable.
