# Athena Ontology Agent Entrypoint Phase67 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route the Athena setup generation button/API entrypoint through `WritingAgentRun` instead of directly calling the legacy setup generator.

**Architecture:** Keep `backend/app/api/setups.py::generate_setup` as the current low-level Hermes setup tool implementation. Change only `POST /api/v1/projects/{project_id}/athena/ontology/generate` so it creates and executes a `WritingAgentRun(entrypoint="athena_ontology_generate")` with tool `generate_setup`, then returns the generated setup plus Agent provenance metadata. This is the first non-dialog UI/API entrypoint migration toward whole-project Agent Service architecture.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, existing `WritingAgentRunService`, existing `generate_setup` Agent tool.

---

## Reference Assimilation

- `openclaw`: UI actions should enter a control-plane task/run abstraction, not call feature code directly.
- `hermes-agent`: preserve tool execution as durable run/step records with inspectable status and output.
- `openhuman`: return compact user-facing results while keeping execution provenance in structured run records.

## Files

- Modify `backend/app/api/athena_ontology.py`
  - Create synchronous Agent run for `/ontology/generate`.
  - Execute `generate_setup`.
  - Return generated setup with `agent_run_id` and `control_plane`.
  - Preserve project-not-found and missing API-key behavior.
- Create `backend/tests/test_athena_ontology_agent.py`
  - Add red test for Agent run creation from Athena ontology generate.
  - Assert generated setup remains available to existing frontend/store contract.
  - Assert missing API key returns 400.
- Add Phase67 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Test For Agent-Backed Athena Setup Generate

- [x] Add a failing test in `backend/tests/test_athena_ontology_agent.py`:

```python
@patch("app.api.setups.load_api_key", return_value="sk-test")
@patch("app.api.setups.ai_service.complete", new_callable=AsyncMock)
@patch("app.api.setups.ai_service.parse_json")
def test_athena_ontology_generate_routes_through_writing_agent_run(
    mock_parse,
    mock_complete,
    mock_key,
    client,
    db_session,
):
    project_id = client.post("/api/v1/projects", json={"name": "Agent Setup Button"}).json()["id"]
    mock_complete.return_value.content = '{"world_building": {}, "characters": [], "core_concept": {}}'
    mock_parse.return_value = {"world_building": {}, "characters": [], "core_concept": {}}

    response = client.post(f"/api/v1/projects/{project_id}/athena/ontology/generate")

    body = response.json()
    run = db_session.query(WritingAgentRun).filter_by(project_id=project_id).one()
    step = db_session.query(WritingAgentStep).filter_by(run_id=run.id).one()
    assert response.status_code == 200
    assert body["status"] == "generated"
    assert body["agent_run_id"] == run.id
    assert body["control_plane"]["source"] == "athena_ontology_generate"
    assert run.entrypoint == "athena_ontology_generate"
    assert run.status == "success"
    assert run.input["control_plane"]["source"] == "athena_ontology_generate"
    assert run.input["tools"][0]["tool_name"] == "generate_setup"
    assert step.tool_name == "generate_setup"
    assert step.status == "success"
    assert step.target_type == "setup"
    assert step.target_id == body["id"]
```

- [x] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_ontology_agent.py -q -k "ontology_generate_routes"
```

Expected before implementation: fails because the endpoint returns setup directly and no `WritingAgentRun` exists.

## Task 2: Missing API Key Compatibility

- [x] Add a regression test:

```python
@patch("app.api.setups.load_api_key", return_value=None)
def test_athena_ontology_generate_preserves_missing_api_key_400(mock_key, client):
    project_id = client.post("/api/v1/projects", json={"name": "Missing Key Agent Setup"}).json()["id"]

    response = client.post(f"/api/v1/projects/{project_id}/athena/ontology/generate")

    assert response.status_code == 400
    assert response.json()["detail"] == "API key not configured"
```

- [x] Run focused RED/GREEN with Task 1 test.

## Task 3: Implement Agent Entrypoint

- [x] In `backend/app/api/athena_ontology.py`, import:

```python
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from app.models import WritingAgentRun, WritingAgentStep
from app.schemas import SetupOut
from app.schemas.writing_agent import WritingAgentRunCreate, WritingAgentToolRequest
from app.services.writing_agent.run_service import WritingAgentRunService
```

- [x] Add constants:

```python
ATHENA_ONTOLOGY_AGENT_CONTROL_PLANE_VERSION = "phase67.athena_ontology_agent.v1"
ATHENA_ONTOLOGY_GENERATE_ENTRYPOINT = "athena_ontology_generate"
```

- [x] Replace direct `generate_setup` wrapper with:

```python
@router.post("/ontology/generate")
async def generate_ontology(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    tool = WritingAgentToolRequest(tool_name="generate_setup")
    run = WritingAgentRunService(db).create_run(
        project_id,
        WritingAgentRunCreate(
            goal="通过 Athena 设定入口生成项目设定",
            entrypoint=ATHENA_ONTOLOGY_GENERATE_ENTRYPOINT,
            tools=[tool],
            input={
                "control_plane": {
                    "version": ATHENA_ONTOLOGY_AGENT_CONTROL_PLANE_VERSION,
                    "source": ATHENA_ONTOLOGY_GENERATE_ENTRYPOINT,
                    "action_type": "generate_setup",
                }
            },
        ),
        effective_tools=[tool],
    )
    run = await WritingAgentRunService(db).execute_run(run.id, [tool])
    if run.status != "success":
        status_code = 400 if run.error == "API key not configured" else 500
        raise HTTPException(status_code=status_code, detail=run.error or "Agent setup generation failed")
    setup = db.query(Setup).filter(Setup.project_id == project_id).order_by(Setup.created_at.desc(), Setup.id.desc()).first()
    if not setup:
        raise HTTPException(status_code=500, detail="Agent setup generation completed without setup output")
    body = jsonable_encoder(SetupOut.model_validate(setup))
    body["agent_run_id"] = run.id
    body["control_plane"] = {
        "version": ATHENA_ONTOLOGY_AGENT_CONTROL_PLANE_VERSION,
        "source": ATHENA_ONTOLOGY_GENERATE_ENTRYPOINT,
    }
    return body
```

## Task 4: Verification

- [x] Run focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_ontology_agent.py -q -k "ontology_generate"
```

- [x] Run related T1/T2 backend tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_ontology_agent.py tests\test_setups.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py -q
```

- [x] Run static checks and secret scan:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

- [x] Write Phase67 report.
- [x] Commit and push to `main`.

## Boundaries

Do:

- make the Athena setup generation button/API enter `WritingAgentRun`;
- preserve the low-level setup generator as the tool implementation for now;
- preserve frontend-compatible setup fields in the response;
- add provenance metadata without requiring frontend changes this phase.

Do not:

- migrate `/setup/generate` itself in this phase;
- migrate chapter/continuous writing yet;
- add a frontend Agent run panel;
- introduce recursion from Agent run back into the Agent API entrypoint;
- replace existing setup prompt or schema.
