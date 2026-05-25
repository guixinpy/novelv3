# Phase140 Chapter Reservation Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Writing Agent inspect which active background tasks reserve a specific chapter target.

**Architecture:** Extend the existing read-only `inspect_agent_job_projection` tool with an optional `chapter_index` selector. When present, the projection narrows queue tasks to jobs covering that chapter and adds a `chapter_reservation` summary with occupying tasks and safe inspection followups.

**Tech Stack:** FastAPI service layer, Writing Agent tool executor/registry, SQLAlchemy models, pytest.

---

## Scope

This phase is read-only. It does not cancel tasks, mutate queues, or automatically retarget chapter generation. It creates the inspection surface needed before later recovery actions.

## Files

- Modify: `backend/app/services/writing_agent/agent_job_projection.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/tests/test_writing_agent_job_projection.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase140-chapter-reservation-projection.md`

## Validation Level

T1:

- Service tests for chapter reservation projection.
- Tool executor adapter test for passing `chapter_index`.
- Tool registry schema test for exposing `chapter_index`.
- Regression on affected backend test files.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_job_projection.py::test_inspect_agent_job_projection_filters_active_chapter_reservation backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_inspect_agent_job_projection_with_chapter_index backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_inspect_agent_job_projection_accepts_chapter_index -q`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_job_projection.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [x] **Step 1: Add service projection test**

Add to `backend/tests/test_writing_agent_job_projection.py`:

```python
def test_inspect_agent_job_projection_filters_active_chapter_reservation(db_session):
    project = Project(name="Agent Job Chapter Reservation")
    db_session.add(project)
    db_session.flush()
    occupying = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter_range",
        status="running",
        payload={"chapter_range": {"start": 2, "end": 4}},
    )
    unrelated = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter",
        status="running",
        payload={"chapter_index": 8},
    )
    db_session.add_all([occupying, unrelated])
    db_session.commit()

    output = inspect_agent_job_projection(db_session, project.id, chapter_index=3)

    assert output["selector"] == {"chapter_index": "3"}
    assert [task["id"] for task in output["tasks"]] == [occupying.id]
    assert output["chapter_reservation"] == {
        "chapter_index": 3,
        "status": "reserved",
        "active_task_count": 1,
        "tasks": [
            {
                "task_id": occupying.id,
                "task_type": "generate_chapter_range",
                "status": "running",
                "source": "range_task",
                "source_label": "批量生成任务",
                "chapter_index": None,
                "chapter_range": {"start": 2, "end": 4},
            }
        ],
        "recommended_tools": ["inspect_agent_job_projection", "inspect_agent_trace_audit"],
        "recovery_options": [
            {
                "action": "inspect_occupying_task",
                "tool_name": "inspect_agent_job_projection",
                "params": {"task_id": occupying.id},
            }
        ],
    }
```

- [x] **Step 2: Add executor adapter test**

Add to `backend/tests/test_writing_agent_tool_executor.py` near the existing `inspect_agent_job_projection` adapter test:

```python
async def test_tool_executor_dispatches_inspect_agent_job_projection_with_chapter_index(db_session, monkeypatch):
    captured = {}

    def fake_projection(db, project_id, *, task_id=None, task_type=None, status=None, limit=None, chapter_index=None):
        captured.update(
            {
                "project_id": project_id,
                "task_id": task_id,
                "task_type": task_type,
                "status": status,
                "limit": limit,
                "chapter_index": chapter_index,
            }
        )
        return {"status": "completed"}

    monkeypatch.setattr(
        "app.services.writing_agent.agent_job_projection.inspect_agent_job_projection",
        fake_projection,
    )
    project = Project(name="Agent Job Projection Adapter")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="inspect_agent_job_projection", params={"chapter_index": 3, "limit": 5}),
    )

    assert result.handled is True
    assert result.output == {"status": "completed"}
    assert captured == {
        "project_id": project.id,
        "task_id": None,
        "task_type": None,
        "status": None,
        "limit": 5,
        "chapter_index": 3,
    }
```

- [x] **Step 3: Add registry schema test**

Add to `backend/tests/test_writing_agent_tool_registry.py`:

```python
def test_agent_tool_registry_inspect_agent_job_projection_accepts_chapter_index():
    descriptor = get_agent_tool_descriptor("inspect_agent_job_projection")
    properties = descriptor.input_schema["properties"]

    assert properties["chapter_index"] == {"type": "integer", "minimum": 1}
```

- [x] **Step 4: Run RED**

Expected:

- Service test fails because `inspect_agent_job_projection` has no `chapter_index` parameter or `chapter_reservation`.
- Executor test fails because adapter does not pass `chapter_index`.
- Registry test fails because schema lacks `chapter_index`.

## Task 2: Minimal Implementation

- [x] **Step 1: Extend service signature and selector**

In `backend/app/services/writing_agent/agent_job_projection.py`, add `chapter_index: int | None = None` to `inspect_agent_job_projection(...)`. Update `_selector(...)` to include `chapter_index` as a string when present.

- [x] **Step 2: Filter queue by chapter coverage**

Add helpers in `agent_job_projection.py`:

```python
CHAPTER_TARGET_SOURCE_LABELS = {
    "single_task": "单章生成任务",
    "range_task": "批量生成任务",
}


def _task_covers_chapter(task: BackgroundTask, chapter_index: int | None) -> bool:
    if chapter_index is None:
        return True
    return chapter_index in _chapter_index_sources_from_task_payload(task.payload if isinstance(task.payload, dict) else {})
```

Add `_chapter_index_sources_from_task_payload(...)` mirroring the current dialog reservation parsing for `chapter_range`, `chapter_index`, `action_params.chapter_index`, and `tools[].params.chapter_index`.

Apply the filter after query filters and before counts:

```python
tasks_for_query = query.order_by(BackgroundTask.created_at.desc(), BackgroundTask.id.desc()).all()
if chapter_index is not None:
    tasks_for_query = [task for task in tasks_for_query if _task_covers_chapter(task, chapter_index)]
total = len(tasks_for_query) if chapter_index is not None else query.with_entities(func.count(BackgroundTask.id)).order_by(None).scalar() or 0
tasks = tasks_for_query[:clamped_limit] if chapter_index is not None else query.order_by(...).limit(clamped_limit).all()
```

- [x] **Step 3: Add `chapter_reservation` output**

Add `_chapter_reservation_projection(tasks, chapter_index)` returning `None` when `chapter_index` is missing. Active statuses are `pending/running`; only active occupying tasks count as reserved.

Expected shape:

```python
{
    "chapter_index": chapter_index,
    "status": "reserved" if active else "available",
    "active_task_count": len(active_tasks),
    "tasks": [_chapter_reservation_task(task, chapter_index) for task in active_tasks],
    "recommended_tools": ["inspect_agent_job_projection", "inspect_agent_trace_audit"] if active_tasks else [],
    "recovery_options": [
        {
            "action": "inspect_occupying_task",
            "tool_name": "inspect_agent_job_projection",
            "params": {"task_id": task.id},
        }
        for task in active_tasks
    ],
}
```

Include this field in the top-level output as `"chapter_reservation": ...`.

- [x] **Step 4: Pass `chapter_index` through executor**

In `backend/app/services/writing_agent/tool_executor.py`, pass:

```python
chapter_index=_optional_int(tool.params.get("chapter_index")),
```

to `inspect_agent_job_projection(...)`.

- [x] **Step 5: Update registry schema**

In `backend/app/services/writing_agent/tool_registry.py`, add:

```python
"chapter_index": {"type": "integer", "minimum": 1},
```

to the `inspect_agent_job_projection` input schema.

## Task 3: Verify, Document, Commit

- [x] Run targeted tests and confirm they pass.
- [x] Run regression subset.
- [x] Run hygiene checks.
- [x] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_job_projection.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_job_projection.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase140-chapter-reservation-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase140-chapter-reservation-projection.md
git commit -m "feat: project chapter task reservations"
git push origin main
```
