# Phase141 Chapter Conflict Recovery Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Agent tool that turns a chapter target conflict into a concrete recovery tool plan.

**Architecture:** Create a focused `chapter_conflict_recovery_planner` service that reuses `inspect_agent_job_projection(..., chapter_index=...)`. Register it as an internal, non-blocking Writing Agent tool. The tool does not cancel tasks or mutate queues; it returns safe next tool requests and recovery options.

**Tech Stack:** Python service layer, Writing Agent tool executor/registry, SQLAlchemy models, pytest.

---

## Scope

This phase adds planning only. It does not execute cancellation, retarget existing tasks, or bypass user approval for write tools.

## Files

- Create: `backend/app/services/writing_agent/chapter_conflict_recovery_planner.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Create: `backend/tests/test_chapter_conflict_recovery_planner.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase141-chapter-conflict-recovery-plan.md`

## Validation Level

T1:

- Planner service tests for available and reserved chapter targets.
- Tool executor adapter test.
- Tool registry schema test.
- Regression on affected backend test files.

Commands:

- Targeted RED/GREEN:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_conflict_recovery_planner.py backend\tests\test_writing_agent_tool_executor.py::test_tool_executor_dispatches_plan_chapter_conflict_recovery_adapter backend\tests\test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_plan_chapter_conflict_recovery -q`
- Regression:
  - `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_conflict_recovery_planner.py backend\tests\test_writing_agent_tool_executor.py backend\tests\test_writing_agent_tool_registry.py backend\tests\test_writing_agent_job_projection.py -q`
- Hygiene:
  - `git diff --check`
  - `rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"`

## Task 1: Failing Tests

- [x] **Step 1: Add planner service tests**

Create `backend/tests/test_chapter_conflict_recovery_planner.py`:

```python
from app.models import BackgroundTask, Project
from app.services.writing_agent.chapter_conflict_recovery_planner import plan_chapter_conflict_recovery


def test_plan_chapter_conflict_recovery_recommends_generation_when_target_available(db_session):
    project = Project(name="Conflict Recovery Available")
    db_session.add(project)
    db_session.commit()

    output = plan_chapter_conflict_recovery(db_session, project.id, chapter_index=2)

    assert output["status"] == "completed"
    assert output["version"] == "phase141.chapter_conflict_recovery.v1"
    assert output["chapter_index"] == 2
    assert output["conflict"]["status"] == "available"
    assert output["recovery"] == {
        "status": "none",
        "reason_code": "chapter_target_available",
        "next_tool": "generate_chapter",
        "next_params": {"chapter_index": 2},
        "should_continue_current_run": True,
        "requires_user_input": False,
    }
    assert output["tools"][0]["tool_name"] == "generate_chapter"
    assert output["tools"][0]["params"] == {"chapter_index": 2}


def test_plan_chapter_conflict_recovery_recommends_inspection_for_reserved_running_task(db_session):
    project = Project(name="Conflict Recovery Reserved")
    db_session.add(project)
    db_session.flush()
    task = BackgroundTask(
        project_id=project.id,
        task_type="generate_chapter_range",
        status="running",
        payload={"chapter_range": {"start": 2, "end": 4}},
    )
    db_session.add(task)
    db_session.commit()

    output = plan_chapter_conflict_recovery(db_session, project.id, chapter_index=3)

    assert output["status"] == "completed"
    assert output["chapter_index"] == 3
    assert output["conflict"]["status"] == "reserved"
    assert output["conflict"]["active_task_count"] == 1
    assert output["recovery"] == {
        "status": "recommended",
        "reason_code": "chapter_target_reserved",
        "next_tool": "inspect_agent_job_projection",
        "next_params": {"task_id": task.id},
        "should_continue_current_run": False,
        "requires_user_input": False,
    }
    assert [tool["tool_name"] for tool in output["tools"]] == [
        "inspect_agent_job_projection",
        "inspect_agent_job_projection",
    ]
    assert output["tools"][0]["params"] == {"chapter_index": 3}
    assert output["tools"][1]["params"] == {"task_id": task.id}
    assert output["recovery_options"][0] == {
        "action": "inspect_occupying_task",
        "tool_name": "inspect_agent_job_projection",
        "params": {"task_id": task.id},
        "safe_auto_execute": True,
    }
    assert output["recovery_options"][1]["action"] == "wait_for_occupying_task"
```

- [x] **Step 2: Add executor adapter test**

Add to `backend/tests/test_writing_agent_tool_executor.py` near other adapter dispatch tests:

```python
@pytest.mark.asyncio
async def test_tool_executor_dispatches_plan_chapter_conflict_recovery_adapter(db_session, monkeypatch):
    project = Project(name="Executor Chapter Conflict Recovery")
    db_session.add(project)
    db_session.commit()
    captured = {}

    def fake_plan(db, project_id: str, *, chapter_index: int | None):
        captured.update({"project_id": project_id, "chapter_index": chapter_index})
        return {"status": "completed", "chapter_index": chapter_index}

    monkeypatch.setattr(
        "app.services.writing_agent.chapter_conflict_recovery_planner.plan_chapter_conflict_recovery",
        fake_plan,
    )

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id),
        WritingAgentToolRequest(tool_name="plan_chapter_conflict_recovery", params={"chapter_index": "3"}),
    )

    assert result.handled is True
    assert result.output == {"status": "completed", "chapter_index": 3}
    assert captured == {"project_id": project.id, "chapter_index": 3}
```

- [x] **Step 3: Add registry schema test**

Add to `backend/tests/test_writing_agent_tool_registry.py`:

```python
def test_agent_tool_registry_includes_plan_chapter_conflict_recovery():
    descriptor = get_agent_tool_descriptor("plan_chapter_conflict_recovery")

    assert descriptor is not None
    assert descriptor.internal is True
    assert descriptor.non_blocking_report is True
    assert descriptor.category == "task_queue"
    assert descriptor.target_type == "agent_tool_plan"
    assert descriptor.input_schema["properties"]["chapter_index"] == {"type": "integer", "minimum": 1}
    assert "plan_chapter_conflict_recovery" in allowed_tool_names()
    assert "plan_chapter_conflict_recovery" in non_blocking_report_tool_names()
```

- [x] **Step 4: Run RED**

Expected:

- Service import fails because `chapter_conflict_recovery_planner.py` does not exist.
- Executor does not handle `plan_chapter_conflict_recovery`.
- Registry has no descriptor.

## Task 2: Minimal Implementation

- [x] **Step 1: Create planner service**

Create `backend/app/services/writing_agent/chapter_conflict_recovery_planner.py`:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.writing_agent.agent_job_projection import inspect_agent_job_projection

CHAPTER_CONFLICT_RECOVERY_VERSION = "phase141.chapter_conflict_recovery.v1"


def plan_chapter_conflict_recovery(db: Session, project_id: str, *, chapter_index: int | None) -> dict[str, Any]:
    if chapter_index is None or int(chapter_index) < 1:
        return {
            "status": "failed",
            "version": CHAPTER_CONFLICT_RECOVERY_VERSION,
            "chapter_index": None,
            "error": "chapter_index is required",
            "tools": [],
            "trace": {"selected_tools": [], "rejected_tools": [{"reason": "missing_chapter_index"}]},
        }
    target = int(chapter_index)
    projection = inspect_agent_job_projection(db, project_id, chapter_index=target)
    reservation = projection.get("chapter_reservation") if isinstance(projection.get("chapter_reservation"), dict) else {}
    conflict = {
        "chapter_index": target,
        "status": reservation.get("status") or "available",
        "active_task_count": int(reservation.get("active_task_count") or 0),
        "tasks": reservation.get("tasks") if isinstance(reservation.get("tasks"), list) else [],
    }
    if conflict["status"] != "reserved":
        tools = [_generate_chapter_tool(target)]
        return {
            "status": "completed",
            "version": CHAPTER_CONFLICT_RECOVERY_VERSION,
            "chapter_index": target,
            "conflict": conflict,
            "recovery": {
                "status": "none",
                "reason_code": "chapter_target_available",
                "next_tool": "generate_chapter",
                "next_params": {"chapter_index": target},
                "should_continue_current_run": True,
                "requires_user_input": False,
            },
            "tools": tools,
            "recovery_options": [],
            "trace": {"selected_tools": ["generate_chapter"], "rejected_tools": []},
        }
    tools = [_inspect_chapter_tool(target)]
    recovery_options = []
    for task in conflict["tasks"]:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if not task_id:
            continue
        inspect_tool = _inspect_task_tool(task_id)
        tools.append(inspect_tool)
        recovery_options.append({**inspect_tool, "action": "inspect_occupying_task", "safe_auto_execute": True})
    recovery_options.append(
        {
            "action": "wait_for_occupying_task",
            "safe_auto_execute": False,
            "reason": "目标章节已有 pending/running 生成任务，继续写入前应等待或人工确认处理。",
        }
    )
    next_params = tools[1]["params"] if len(tools) > 1 else {"chapter_index": target}
    return {
        "status": "completed",
        "version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        "chapter_index": target,
        "conflict": conflict,
        "recovery": {
            "status": "recommended",
            "reason_code": "chapter_target_reserved",
            "next_tool": "inspect_agent_job_projection",
            "next_params": next_params,
            "should_continue_current_run": False,
            "requires_user_input": False,
        },
        "tools": tools,
        "recovery_options": recovery_options,
        "trace": {"selected_tools": [str(tool["tool_name"]) for tool in tools], "rejected_tools": []},
    }


def _generate_chapter_tool(chapter_index: int) -> dict[str, Any]:
    return {
        "tool_name": "generate_chapter",
        "params": {"chapter_index": chapter_index},
        "planner": {
            "reason": "目标章节未被后台任务占用，可以继续生成。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "生成目标章节正文。",
            "post_generation": True,
            "planner_version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        },
    }


def _inspect_chapter_tool(chapter_index: int) -> dict[str, Any]:
    return {
        "tool_name": "inspect_agent_job_projection",
        "params": {"chapter_index": chapter_index},
        "planner": {
            "reason": "先查看目标章节的占用投影。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "返回目标章节的后台任务占用信息。",
            "post_generation": False,
            "planner_version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        },
    }


def _inspect_task_tool(task_id: str) -> dict[str, Any]:
    return {
        "tool_name": "inspect_agent_job_projection",
        "params": {"task_id": task_id},
        "planner": {
            "reason": "查看占用该章节的具体后台任务。",
            "on_missing": "stop",
            "on_failure": "stop",
            "expected_output": "返回占用任务详情、恢复建议和关联 Agent run。",
            "post_generation": False,
            "planner_version": CHAPTER_CONFLICT_RECOVERY_VERSION,
        },
    }
```

- [x] **Step 2: Add executor adapter**

In `backend/app/services/writing_agent/tool_executor.py`, add handler:

```python
def _plan_chapter_conflict_recovery(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_conflict_recovery_planner import plan_chapter_conflict_recovery

    return plan_chapter_conflict_recovery(
        context.db,
        context.project_id,
        chapter_index=_optional_int(tool.params.get("chapter_index")),
    )
```

Register it in `ADAPTERS`:

```python
"plan_chapter_conflict_recovery": WritingAgentToolAdapter(
    "plan_chapter_conflict_recovery",
    _plan_chapter_conflict_recovery,
    category="task_queue",
    mutability="read",
),
```

- [x] **Step 3: Add registry descriptor**

In `backend/app/services/writing_agent/tool_registry.py`, add an `AgentToolDescriptor` near task queue tools:

```python
AgentToolDescriptor(
    name="plan_chapter_conflict_recovery",
    module="writing_agent",
    category="task_queue",
    description="根据目标章节占用投影生成只读冲突恢复工具计划，不直接取消或重排任务。",
    input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}}, required=("chapter_index",)),
    output_schema=_object_schema(
        {
            "status": {"type": "string"},
            "version": {"type": "string"},
            "chapter_index": {"type": "integer"},
            "conflict": {"type": "object"},
            "recovery": {"type": "object"},
            "tools": {"type": "array"},
            "recovery_options": {"type": "array"},
            "trace": {"type": "object"},
        }
    ),
    target_type="agent_tool_plan",
    internal=True,
    non_blocking_report=True,
    sort_key=10,
    availability_checks=("project_exists",),
),
```

## Task 3: Verify, Document, Commit

- [x] Run targeted tests and confirm they pass.
- [x] Run regression subset.
- [x] Run hygiene checks.
- [x] Wait for/reference the architecture explorer result if available; if unavailable, note that in the report.
- [x] Write phase report with RED/GREEN evidence.
- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/chapter_conflict_recovery_planner.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_chapter_conflict_recovery_planner.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase141-chapter-conflict-recovery-plan.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase141-chapter-conflict-recovery-plan.md
git commit -m "feat: plan chapter conflict recovery"
git push origin main
```
