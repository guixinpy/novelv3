# Writing Task Control Plane Phase71 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make writing task creation itself Agent-control-plane aware, not only the chapter generation work executed later.

**Architecture:** Keep the existing `generate_chapter` and `retry_chapter` background task types so queue behavior remains stable. Add a compact `control_plane` payload to tasks created by `/writing/start`, `/writing/resume`, and `/writing/chapters/{chapter_index}/retry`, then surface that same metadata in `WritingControlOut` responses. This is an incremental service-layer bridge toward a full Agent-orchestrated task queue.

**Tech Stack:** FastAPI, SQLAlchemy JSON payloads, Pydantic response models, pytest.

---

## Context

Phase69 made direct chapter generation create `WritingAgentRun` records. Phase70 preserved those run IDs in background task results. The remaining gap is earlier in the flow: the task queue entry created by writing start/resume/retry still looks like a plain queue task, so the Agent service has no durable creation-time control-plane metadata.

The user clarified this goal is not about slash commands only. The whole project must become an Agent service where existing modules are tools and long-running workflows are auditable Agent actions.

## Reference Assimilation

- `openclaw`: user-facing actions should become durable control-plane tasks, not hidden implementation calls.
- `hermes-agent`: tool execution should carry a stable entrypoint/version/source so runs can be audited.
- `openhuman`: long-running work should keep compact creation metadata separate from verbose execution results.

## Files

- Modify `backend/app/api/writing.py`
  - Add task control-plane version constant.
  - Add helper for writing task `control_plane`.
  - Pass source-specific metadata from start, resume, and retry.
  - Include task `control_plane` in `_control_out()`.
- Modify `backend/app/schemas/writing.py`
  - Add optional `control_plane` field to `WritingControlOut`.
- Modify `backend/tests/test_writing.py`
  - Update exact payload tests.
  - Assert API response exposes the same control-plane metadata.
- Add Phase71 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Tests For Start/Resume/Retry Control Plane

- [ ] Update existing payload assertions in `backend/tests/test_writing.py` so new tasks must include:

```python
"control_plane": {
    "version": "phase71.writing_task_control_plane.v1",
    "source": "writing_start",
    "entrypoint": "continuous_writing_generate",
    "tool_name": "generate_chapter",
    "chapter_index": 1,
}
```

- [ ] Add response assertions:

```python
assert response.json()["control_plane"] == task.payload["control_plane"]
```

- [ ] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "creates_generate_chapter_task or creates_range_task_when_target_is_known or after_completed_chapter_queues_next_chapter or resume_creates_generate_chapter_task or retry_creates_background_task"
```

Expected before implementation: failures because task payloads and responses do not include `control_plane`.

## Task 2: Minimal Implementation

- [ ] Add in `backend/app/api/writing.py`:

```python
WRITING_TASK_CONTROL_PLANE_VERSION = "phase71.writing_task_control_plane.v1"


def _writing_task_control_plane(
    *,
    source: str,
    entrypoint: str,
    tool_name: str,
    chapter_index: int,
) -> dict:
    return {
        "version": WRITING_TASK_CONTROL_PLANE_VERSION,
        "source": source,
        "entrypoint": entrypoint,
        "tool_name": tool_name,
        "chapter_index": int(chapter_index),
    }
```

- [ ] Change `_queue_generate_chapter_task()` signature:

```python
def _queue_generate_chapter_task(db: Session, project_id: str, chapter_index: int, *, source: str) -> BackgroundTask:
```

- [ ] Pass `source="writing_start"` and `source="writing_resume"` from the two API endpoints.
- [ ] Add `control_plane` to newly created task payloads.
- [ ] Add retry control plane with `source="writing_retry"`, `entrypoint="continuous_writing_retry"`, `tool_name="retry_chapter"`.
- [ ] Add optional `control_plane` to `WritingControlOut` and `_control_out()`.

## Task 3: GREEN Verification

- [ ] Run focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q -k "creates_generate_chapter_task or creates_range_task_when_target_is_known or after_completed_chapter_queues_next_chapter or resume_creates_generate_chapter_task or retry_creates_background_task"
```

- [ ] Run related writing regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing.py -q
```

- [ ] Run static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

## Boundaries

Do:

- preserve existing task types and queue semantics;
- keep old active-task reuse compatible;
- expose compact control-plane metadata in API responses.

Do not:

- rename task types;
- convert queue execution to a full Agent planner in this phase;
- run real model generation;
- change frontend behavior yet.
