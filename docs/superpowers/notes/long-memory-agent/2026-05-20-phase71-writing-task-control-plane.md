# Phase71 Report: Writing Task Control Plane

## Summary

Phase71 makes writing task creation Agent-control-plane aware.

Before this phase, Phase69 and Phase70 already let chapter generation create `WritingAgentRun` records and preserve run provenance in task results. The gap was earlier: `/writing/start`, `/writing/resume`, and `/writing/chapters/{chapter_index}/retry` still created plain `BackgroundTask` payloads with only `chapter_index`.

Now newly created writing tasks include compact `control_plane` metadata, and `WritingControlOut` surfaces the same metadata to API callers.

## Scope Correction

The user clarified that this goal is not limited to slash commands. The entire project must be transformed into an Agent service. Existing modules such as Hermes, Athena, world model, retrieval, knowledge base, review, task queue, and Trace should gradually become Agent-callable services/tools.

This phase is a narrow step in that direction: it makes the task queue entry created by writing controls visible as an Agent-controlled action.

## Changes

- Updated `backend/app/api/writing.py`.
- Updated `backend/app/schemas/writing.py`.
- Updated `backend/tests/test_writing.py`.
- Added `WRITING_TASK_CONTROL_PLANE_VERSION = "phase71.writing_task_control_plane.v1"`.
- Added `_writing_task_control_plane()`.
- `/writing/start` now creates generate tasks with:
  - `source: writing_start`
  - `entrypoint: continuous_writing_generate`
  - `tool_name: generate_chapter`
- `/writing/resume` now creates generate tasks with:
  - `source: writing_resume`
  - `entrypoint: continuous_writing_generate`
  - `tool_name: generate_chapter`
- `/writing/chapters/{chapter_index}/retry` now creates retry tasks with:
  - `source: writing_retry`
  - `entrypoint: continuous_writing_retry`
  - `tool_name: retry_chapter`
- `WritingControlOut` now optionally includes `control_plane`.

## Result Contract

New generate task payload:

```json
{
  "chapter_index": 1,
  "control_plane": {
    "version": "phase71.writing_task_control_plane.v1",
    "source": "writing_start",
    "entrypoint": "continuous_writing_generate",
    "tool_name": "generate_chapter",
    "chapter_index": 1
  }
}
```

New range task payload preserves existing `chapter_range`:

```json
{
  "chapter_index": 1,
  "control_plane": {
    "version": "phase71.writing_task_control_plane.v1",
    "source": "writing_start",
    "entrypoint": "continuous_writing_generate",
    "tool_name": "generate_chapter",
    "chapter_index": 1
  },
  "chapter_range": {
    "start": 1,
    "end": 3
  }
}
```

New retry task payload:

```json
{
  "chapter_index": 2,
  "control_plane": {
    "version": "phase71.writing_task_control_plane.v1",
    "source": "writing_retry",
    "entrypoint": "continuous_writing_retry",
    "tool_name": "retry_chapter",
    "chapter_index": 2
  }
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "creates_generate_chapter_task or creates_range_task_when_target_is_known or after_completed_chapter_queues_next_chapter or resume_creates_generate_chapter_task or retry_creates_background_task"
```

Result before implementation: `5 failed`; all failures showed task payloads lacked `control_plane`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "creates_generate_chapter_task or creates_range_task_when_target_is_known or after_completed_chapter_queues_next_chapter or resume_creates_generate_chapter_task or retry_creates_background_task"
```

Result: `5 passed, 25 deselected in 0.36s`.

Writing regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q
```

Result: `30 passed in 1.87s`.

Related queue regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py tests\test_background.py -q
```

Result: `65 passed in 3.88s`.

## Subagent Architecture Probe

Read-only architecture probe result:

- Current Agent backbone already exists: `WritingAgentRun/Step`, tool registry, tool executor, and several API control-plane bridges.
- The next useful work is not to keep adding isolated generation endpoints.
- The next useful work is to make core subsystems Agent-callable services:
  - retrieval and longform memory route;
  - Trace/context audit route;
  - world model fact/query/impact route;
  - generic Agent job queue contract;
  - knowledge base for author memory, project strategy, and self-optimization experience.

Recommended next phase order:

1. Agent memory route: retrieval + longform memory + diagnostics.
2. Trace audit tool: explain run/chapter/task context and failure chain.
3. World model query/impact tools: read-only facts, snapshots, proposal pressure, conflict explanations.
4. Generic Agent job contract: inspect/resume/cancel/retry projection for Agent jobs.
5. Knowledge base minimum loop: author memory, project strategy, self-optimization experience, without polluting world facts.

## Novel Progress

No production novel chapter was generated in this phase. The phase focused on making long-running writing controls auditable before further dogfood generation.

## Fixed Issues

- Writing start/resume tasks now have creation-time control-plane metadata.
- Writing retry tasks now have creation-time control-plane metadata.
- Writing control API responses can expose the task control plane.

## Remaining Boundary

This phase does not yet convert `BackgroundTask` into a full Agent job ledger. It preserves the existing queue contract and adds metadata. The next phases should move from metadata bridges to actual Agent service contracts for memory, Trace, world model queries, and task orchestration.
