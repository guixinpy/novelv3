# Athena Evolution Agent Entrypoint Phase68 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route Athena evolution plan generation for storyline and outline through `WritingAgentRun`.

**Architecture:** Keep `storylines.generate_storyline()` and `outlines.generate_outline()` as low-level Hermes tool implementations. Change `POST /api/v1/projects/{project_id}/athena/evolution/plan/generate` to create and execute an Agent run with `generate_storyline` or `generate_outline`, then return the existing full/windowed response plus compact Agent provenance. Extract a small API control-plane helper shared with the Phase67 ontology entrypoint to avoid duplicating Agent run creation logic.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, existing `WritingAgentRunService`, existing generation tools.

---

## Reference Assimilation

- `openclaw`: command/UI/API intents normalize into control-plane tool calls.
- `hermes-agent`: each tool call is represented by durable run/step state.
- `openhuman`: outward response stays compact; internal execution detail remains inspectable.

## Files

- Create `backend/app/services/writing_agent/api_control_plane.py`
  - Shared helper for synchronous API Agent tool execution.
- Modify `backend/app/api/athena_ontology.py`
  - Reuse shared helper from Phase67 behavior.
- Modify `backend/app/api/athena_evolution.py`
  - Route target `storyline` to tool `generate_storyline`.
  - Route target `outline` to tool `generate_outline`.
  - Preserve `response_mode=full|window`.
- Modify `backend/tests/test_athena_evolution_generation_windows.py`
  - Add Agent run assertions for storyline and outline window generation.
  - Add missing API key compatibility regression.
- Keep `backend/tests/test_athena_ontology_agent.py` passing.

## Task 1: RED Storyline Agent Run Test

- [x] Extend `test_athena_storyline_generate_defaults_to_windowed_response`:

```python
run = db_session.query(WritingAgentRun).filter_by(project_id=project.id).one()
step = db_session.query(WritingAgentStep).filter_by(run_id=run.id).one()
assert data["agent_run_id"] == run.id
assert data["control_plane"]["source"] == "athena_evolution_plan_generate"
assert data["control_plane"]["target"] == "storyline"
assert run.entrypoint == "athena_evolution_plan_generate"
assert run.input["tools"][0]["tool_name"] == "generate_storyline"
assert step.tool_name == "generate_storyline"
assert step.status == "success"
assert step.target_type == "storyline"
assert step.target_id == stored.id
```

- [x] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_evolution_generation_windows.py -q -k "storyline_generate"
```

Expected before implementation: fails because no `WritingAgentRun` exists and response has no provenance.

## Task 2: RED Outline Agent Run Test

- [x] Extend `test_athena_outline_generate_defaults_to_windowed_response`:

```python
run = db_session.query(WritingAgentRun).filter_by(project_id=project.id).one()
step = db_session.query(WritingAgentStep).filter_by(run_id=run.id).one()
assert data["agent_run_id"] == run.id
assert data["control_plane"]["source"] == "athena_evolution_plan_generate"
assert data["control_plane"]["target"] == "outline"
assert run.entrypoint == "athena_evolution_plan_generate"
assert run.input["tools"][0]["tool_name"] == "generate_outline"
assert step.tool_name == "generate_outline"
assert step.status == "success"
assert step.target_type == "outline"
assert step.target_id == stored.id
```

## Task 3: Missing API Key Compatibility

- [x] Add test:

```python
@patch("app.api.outlines.load_api_key", return_value=None)
def test_athena_evolution_outline_generate_preserves_missing_api_key_400(mock_key, client, db_session):
    project = Project(name="Missing Key Outline Agent")
    db_session.add(project)
    db_session.flush()
    db_session.add(Setup(project_id=project.id, status="generated", world_building={}, characters=[], core_concept={}))
    db_session.add(Storyline(project_id=project.id, status="generated", plotlines=[], foreshadowing=[]))
    db_session.commit()

    response = client.post(f"/api/v1/projects/{project.id}/athena/evolution/plan/generate?target=outline")

    assert response.status_code == 400
    assert response.json()["detail"] == "API key not configured"
```

## Task 4: Shared API Control Plane Helper

- [x] Create `backend/app/services/writing_agent/api_control_plane.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentRun
from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
from app.services.writing_agent.run_service import WritingAgentRunService


@dataclass(frozen=True)
class AgentApiToolRunResult:
    run: WritingAgentRun
    control_plane: dict[str, Any]


async def execute_agent_api_tool(
    db: Session,
    *,
    project_id: str,
    entrypoint: str,
    version: str,
    source: str,
    action_type: str,
    tool_name: str,
    goal: str,
    command_args: str | None = None,
    params: dict[str, Any] | None = None,
    extra_control_plane: dict[str, Any] | None = None,
) -> AgentApiToolRunResult:
    control_plane = {
        "version": version,
        "source": source,
        "action_type": action_type,
        **(extra_control_plane or {}),
    }
    tool = WritingAgentToolRequest(tool_name=tool_name, command_args=command_args, params=params or {})
    service = WritingAgentRunService(db)
    run = service.create_run(
        project_id,
        WritingAgentRunCreate(
            goal=goal,
            entrypoint=entrypoint,
            tools=[tool],
            input={"control_plane": control_plane},
        ),
        effective_tools=[tool],
    )
    run = await service.execute_run(run.id, [tool])
    return AgentApiToolRunResult(run=run, control_plane=control_plane)
```

## Task 5: Implementation

- [x] Refactor `athena_ontology.generate_ontology()` to use `execute_agent_api_tool`.
- [x] Update `athena_evolution.generate_evolution_plan()`:
  - validate project;
  - pick tool based on target;
  - execute Agent run;
  - map known legacy validation errors to 400;
  - fetch existing window/full response;
  - attach `agent_run_id` and `control_plane`.

Known 400 legacy errors:

- `API key not configured`
- `Setup not generated yet`
- `Storyline not generated yet`

## Task 6: Verification

- [x] Run focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_evolution_generation_windows.py tests\test_athena_ontology_agent.py -q -k "generate"
```

- [x] Run related T1/T2 backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_evolution_generation_windows.py tests\test_athena_ontology_agent.py tests\test_storylines.py tests\test_outlines.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py -q
```

- [x] Static checks and secret scan:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

- [x] Write Phase68 report.
- [x] Commit and push to `main`.

## Boundaries

Do:

- migrate Athena evolution generate wrappers into Agent runs;
- preserve response shape for window/full modes;
- add provenance metadata non-disruptively;
- reuse the helper for Phase67 setup generation.

Do not:

- migrate direct `/storyline/generate` or `/outline/generate` this phase;
- migrate chapter or continuous writing yet;
- change generation prompts;
- add frontend UI for Agent runs yet.
