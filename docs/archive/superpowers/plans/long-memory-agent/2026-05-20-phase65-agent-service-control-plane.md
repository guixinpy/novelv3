# Agent Service Control Plane Phase65 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Start migrating novelv3's user-facing control plane into Writing Agent runs, using confirmed Hermes creation actions as the first end-to-end Agent Service slice.

**Architecture:** Keep the existing chat and confirmation UI contract, but change confirmed creative actions from direct `ActionExecutionService` background execution to a `WritingAgentRun` executed by a background task. The legacy slash-command module becomes a compatibility intent shortcut; the durable execution record becomes Agent run/step/Trace. This is the first slice of the broader Agent Service migration, not a slash-command-only fix.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing `WritingAgentRunService`, `BackgroundTaskService`, `LocalTaskRunner`, existing dialog schemas, pytest.

---

## Reference Assimilation

Phase65 adopts these mechanisms from the three reference projects:

- `openclaw`: local commands are control-plane shortcuts, not hidden execution paths; tool visibility and state gating remain explicit.
- `hermes-agent`: agent loops need durable run state, bounded execution, and explicit exit status.
- `openhuman`: parent context should receive compact structured results, not raw internal execution transcripts.

Translated to novelv3:

- user input and slash commands become `entrypoint` metadata and intent shortcuts;
- execution goes through `WritingAgentRun` and typed tools;
- dialog history receives a concise terminal message with `agent_run_id`, while detailed steps stay in Agent run records.

## File Structure

- Create `backend/app/services/writing_agent/dialog_control_plane.py`
  - Map confirmed dialog actions to Writing Agent tool requests.
  - Create a linked background task for Agent run execution.
  - Build background work that executes the run and writes a concise dialog result message.
  - Keep unsupported actions on the existing legacy path for now.
- Modify `backend/app/services/writing_agent/run_service.py`
  - Allow `create_run()` to persist dialog linkage and background task linkage.
- Modify `backend/app/api/dialogs.py`
  - On confirmed supported creative actions, route through the new Agent control plane.
  - Return `agent_run_id` and `task_id` in `action_result.data`.
  - Preserve `/clear`, `/compact`, pending action creation, cancellation, and revise behavior.
- Modify `backend/app/services/actions/action_result_service.py`
  - Add a reusable method for recording Agent-run-backed action completion messages, or keep completion formatting in `dialog_control_plane.py` if narrower.
- Modify backend tests:
  - `backend/tests/test_dialogs.py`
  - `backend/tests/test_writing_agent_runs.py` only if run-service linkage needs direct coverage.

## Task 1: Dialog Action To Agent Tool Mapping

- [x] Add failing tests in `backend/tests/test_dialogs.py`:
  - confirmed `/setup` action creates a `WritingAgentRun`;
  - run has `entrypoint == "dialog_pending_action"`;
  - run is linked to `dialog_id` and `background_task_id`;
  - run input contains `control_plane.version == "phase65.agent_control_plane.v1"`;
  - run tools contain `generate_setup`;
  - resolve response includes `action_result.data.agent_run_id`.

Expected test shape:

```python
def test_resolve_action_confirm_routes_setup_through_writing_agent_run(client, db_session, monkeypatch):
    started = []
    monkeypatch.setattr("app.api.dialogs.LocalTaskRunner.start", lambda self, task_id, work: started.append(task_id))
    project_id = _create_project(client, "Agent Control Plane")
    pending = client.post(
        "/api/v1/dialog/chat",
        json={
            "project_id": project_id,
            "input_type": "command",
            "command_name": "setup",
            "command_args": "雾港悬疑，主角是记忆取证师",
        },
    ).json()["pending_action"]

    response = client.post(
        "/api/v1/dialog/resolve-action",
        json={"action_id": pending["id"], "decision": "confirm"},
    )

    body = response.json()
    run = db_session.query(WritingAgentRun).filter_by(project_id=project_id).one()
    task = db_session.query(BackgroundTask).filter_by(id=body["action_result"]["data"]["task_id"]).one()
    assert response.status_code == 200
    assert body["action_result"]["data"]["agent_run_id"] == run.id
    assert run.entrypoint == "dialog_pending_action"
    assert run.dialog_id is not None
    assert run.background_task_id == task.id
    assert run.input["control_plane"]["version"] == "phase65.agent_control_plane.v1"
    assert run.input["tools"][0]["tool_name"] == "generate_setup"
    assert task.task_type == "writing_agent_run"
    assert started == [task.id]
```

- [x] Add the mapping service in `backend/app/services/writing_agent/dialog_control_plane.py`.

Core behavior:

```python
CONTROL_PLANE_VERSION = "phase65.agent_control_plane.v1"
SUPPORTED_DIALOG_ACTION_TO_TOOL = {
    "generate_setup": "generate_setup",
    "generate_storyline": "generate_storyline",
    "generate_outline": "generate_outline",
    "generate_chapter": "generate_chapter",
}
```

- [x] Run focused RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "agent_control_plane or routes_setup_through_writing_agent_run"
```

Expected before implementation: fails because no Agent run is created.

## Task 2: Run Service Dialog Linkage

- [x] Modify `WritingAgentRunService.create_run()` signature:

```python
def create_run(
    self,
    project_id: str,
    payload: WritingAgentRunCreate,
    *,
    effective_tools: list[WritingAgentToolRequest] | None = None,
    planner_output: dict[str, Any] | None = None,
    dialog_id: str | None = None,
    request_message_id: str | None = None,
    response_message_id: str | None = None,
    background_task_id: str | None = None,
) -> WritingAgentRun:
```

- [x] Persist those fields on `WritingAgentRun`.
- [x] Keep existing API callers unchanged by defaulting all new params to `None`.
- [x] Run existing Agent API smoke:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "create_agent_run_records_steps_and_returns_detail"
```

Expected: pass.

## Task 3: Background Agent Run Execution From Dialog

- [x] Add a second failing test in `backend/tests/test_dialogs.py`:
  - use `LocalTaskRunner.run_now()` or call the new work function directly;
  - monkeypatch `ActionExecutionService.execute` to return success;
  - assert the run becomes `success`;
  - assert the dialog receives a terminal system message with `action_result.data.agent_run_id`;
  - assert the terminal message does not include raw step transcript.

Expected test shape:

```python
@pytest.mark.asyncio
async def test_dialog_agent_control_plane_background_work_records_terminal_message(db_session, monkeypatch):
    project = Project(name="Agent Work")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    tools = [WritingAgentToolRequest(tool_name="generate_setup", command_args="雾港悬疑")]
    payload = WritingAgentRunCreate(
        goal="通过对话确认执行 generate_setup",
        entrypoint="dialog_pending_action",
        tools=tools,
        input={"control_plane": {"version": "phase65.agent_control_plane.v1"}},
    )
    run = WritingAgentRunService(db_session).create_run(project.id, payload, effective_tools=tools, dialog_id=dialog.id)
    task = BackgroundTaskService(db_session).create(project_id=project.id, task_type="writing_agent_run", payload={"agent_run_id": run.id})
    run.background_task_id = task.id
    db_session.commit()

    async def fake_execute(self, action_type, project_id, *, command_args=None, action_params=None):
        return {"status": "success", "trace_id": None}

    monkeypatch.setattr("app.services.actions.action_execution_service.ActionExecutionService.execute", fake_execute)
    work = build_dialog_agent_run_background_work(
        run_id=run.id,
        tools=[tool.model_dump() for tool in tools],
        dialog_id=dialog.id,
        action_type="generate_setup",
        command_args="雾港悬疑",
        action_params={"project_id": project.id},
    )
    result = await work(db_session, task)

    terminal = db_session.query(DialogMessage).filter_by(dialog_id=dialog.id, role="system").one()
    assert result["agent_run_id"] == run.id
    assert db_session.query(WritingAgentRun).filter_by(id=run.id).one().status == "success"
    assert terminal.action_result["data"]["agent_run_id"] == run.id
    assert "steps" not in terminal.action_result["data"]
```

- [x] Implement `build_dialog_agent_run_background_work()`.
- [x] For success, record `status: "success"` and include:
  - `agent_run_id`;
  - `background_task_id`;
  - last successful step's public output summary;
  - `trace_id` when available.
- [x] For blocked or failed, record terminal dialog message with status `blocked` or `failed`.
- [x] Avoid throwing for blocked/failed Agent runs unless the runner itself crashes.

## Task 4: Wire Resolve Action To Agent Control Plane

- [x] In `backend/app/api/dialogs.py`, after `preview_action_to_execution()`, route supported creative actions through `dialog_control_plane`.
- [x] Keep unsupported actions on `_execute_action_background()` for compatibility.
- [x] Return response data:

```python
result_data = {
    "status": "generating",
    "task_id": task.id,
    "agent_run_id": run.id,
    "control_plane": {"version": "phase65.agent_control_plane.v1"},
}
```

- [x] Ensure cancellation and revise do not create Agent runs.
- [x] Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py -q -k "agent_control_plane or routes_setup_through_writing_agent_run or background_work_records_terminal_message"
```

Expected: pass.

## Task 5: Regression And Report

- [x] Run dialog + Agent related T1:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_dialogs.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

- [x] Run static checks and secret scan:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

- [x] Write Phase65 report:
  - `docs/superpowers/notes/long-memory-agent/2026-05-20-phase65-agent-service-control-plane.md`
- [ ] Commit and push to `main`.

## Boundaries

Do:

- make confirmed creative dialog actions create real `WritingAgentRun` records;
- preserve current chat UI and pending confirmation flow;
- keep `LocalTaskRunner` as the async execution shell;
- keep old `/clear` and `/compact` behavior;
- return both `task_id` and `agent_run_id`;
- make terminal dialog messages compact and inspectable.

Do not:

- rewrite all direct generation endpoints in this phase;
- migrate continuous writing `/writing/start` and `/writing/resume` yet;
- build a new frontend Agent panel yet;
- expose all Agent step transcripts inside chat messages;
- remove `PendingAction` before the replacement confirmation UX exists;
- auto-approve world-model truth mutations.
