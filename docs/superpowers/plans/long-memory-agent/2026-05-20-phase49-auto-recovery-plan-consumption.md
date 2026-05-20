# Phase49 Auto Recovery Plan Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `input.auto_plan` consume a prior run's recovery plan through an explicit `recovery_run_id`, producing executable recovery tools without changing step execution semantics.

**Architecture:** Keep `execute_run()` static and auditable. Add a recovery branch in `WritingAgentRunService.build_auto_plan_tools()` that calls `build_recovery_tool_plan()` and converts its `tools` into `WritingAgentToolRequest` instances. The recovery branch only triggers when `payload.tools` is empty, `input.auto_plan is True`, and `input.recovery_run_id` is present.

**Tech Stack:** FastAPI service layer, SQLAlchemy session, Pydantic `WritingAgentToolRequest`, pytest API tests.

---

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Add API test for recovery auto-plan execution**

Add `test_agent_run_auto_plan_consumes_recovery_tool_plan`:

```python
def test_agent_run_auto_plan_consumes_recovery_tool_plan(client, db_session, monkeypatch):
    project = _seed_longform_project(db_session, outline_chapters=[1], generated_chapters=[1, 2])
    blocked = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "检查第3章是否可写",
            "tools": [{"tool_name": "preflight_writing", "params": {"chapter_index": 3}}],
        },
    )
    blocked_run_id = blocked.json()["id"]

    class FakeOutline:
        id = "outline-recovery-3"
        total_chapters = 600
        outline_expansion_result = {"added_chapter_count": 1}
        last_expansion_trace_id = None

    async def fake_expand_outline_window(project_id, *, start_chapter, end_chapter, db, command_args=None):
        assert project_id == project.id
        assert start_chapter == 3
        assert end_chapter == 3
        return FakeOutline()

    monkeypatch.setattr("app.api.outlines.expand_outline_window", fake_expand_outline_window)

    response = client.post(
        f"/api/v1/projects/{project.id}/agent-runs",
        json={
            "goal": "恢复上一轮阻塞",
            "input": {"auto_plan": True, "recovery_run_id": blocked_run_id},
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "success"
    assert payload["input"]["planner"]["source_run_id"] == blocked_run_id
    assert payload["input"]["planner"]["trace"]["selected_tools"] == ["expand_outline_window"]
    assert payload["input"]["tools"][0]["tool_name"] == "expand_outline_window"
    assert payload["input"]["tools"][0]["params"] == {"start_chapter": 3, "end_chapter": 3}
    assert [step["tool_name"] for step in payload["steps"]] == ["expand_outline_window"]
    assert payload["steps"][0]["input"]["planner"]["planner_version"] == "phase48.recovery_planner.v1"
```

- [x] **Step 2: Verify RED**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_consumes_recovery"
```

Expected: FAIL because `input.recovery_run_id` is ignored by auto-plan.

## Task 2: Implement Auto-Plan Recovery Branch

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Add explicit recovery run id extraction**

Inside `build_auto_plan_tools()`, after confirming `auto_plan is True`, read:

```python
recovery_run_id = str(run_input.get("recovery_run_id") or "").strip() or None
```

- [x] **Step 2: Convert recovery plan tools into executable requests**

If `recovery_run_id` exists, call `build_recovery_tool_plan()` and return:

```python
tools = [WritingAgentToolRequest(**tool) for tool in plan.get("tools", []) if isinstance(tool, dict)]
return tools, plan
```

Do not execute `plan_recovery_tools`; consume the shared planner helper directly.

## Task 3: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase49-auto-recovery-plan-consumption.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_consumes_recovery"
```

- [x] **Step 2: Run T1 module verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 3: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 4: Write report, commit, push**
