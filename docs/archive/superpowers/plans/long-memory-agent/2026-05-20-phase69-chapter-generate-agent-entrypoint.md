# Chapter Generate Agent Entrypoint Phase69 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route direct chapter generation API through `WritingAgentRun`.

**Architecture:** Keep `create_or_replace_chapter()` as the low-level Hermes chapter tool implementation. Change `POST /api/v1/projects/{project_id}/chapters/{chapter_index}/generate` so it creates and executes a `WritingAgentRun(entrypoint="chapter_generate")` with tool `generate_chapter`, then returns the existing `ChapterOut` payload plus Agent provenance metadata. Continuous writing remains unchanged this phase and can later reuse the same Agent tool contract.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, existing `execute_agent_api_tool`, existing `generate_chapter` Agent tool.

---

## Reference Assimilation

- `openclaw`: direct UI/API actions should enter a run/task control plane.
- `hermes-agent`: creative generation should leave durable tool-run/step traces.
- `openhuman`: return compact chapter output while storing execution provenance in Agent records.

## Files

- Modify `backend/app/api/chapters.py`
  - Route direct chapter generation endpoint through `execute_agent_api_tool`.
  - Return existing chapter payload with `agent_run_id` and `control_plane`.
  - Preserve known legacy HTTP 400/404 behavior.
- Modify `backend/app/schemas/chapter.py`
  - Add optional provenance fields so FastAPI response model does not strip metadata.
- Modify `backend/tests/test_chapters.py`
  - Extend direct generation test with Agent run/step assertions.
  - Add missing API key compatibility regression if existing coverage does not prove endpoint mapping.
- Add Phase69 report under `docs/superpowers/notes/long-memory-agent/`.

## Task 1: RED Chapter Endpoint Agent Run Test

- [x] Extend `backend/tests/test_chapters.py::test_generate_chapter`:

```python
run = db_session.query(WritingAgentRun).filter_by(project_id=pid).one()
step = db_session.query(WritingAgentStep).filter_by(run_id=run.id).one()
body = r2.json()
assert body["agent_run_id"] == run.id
assert body["control_plane"]["source"] == "chapter_generate"
assert body["control_plane"]["chapter_index"] == 1
assert run.entrypoint == "chapter_generate"
assert run.status == "success"
assert run.input["tools"][0]["tool_name"] == "generate_chapter"
assert run.input["tools"][0]["params"] == {"chapter_index": 1}
assert step.tool_name == "generate_chapter"
assert step.status == "success"
assert step.target_type == "chapter"
assert step.chapter_index == 1
```

- [x] Run RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py -q -k "test_generate_chapter"
```

Expected before implementation: fails because no Agent run exists and response has no provenance.

## Task 2: Missing API Key Compatibility

- [x] Add or update a regression test:

```python
@patch("app.api.chapters.load_api_key", return_value=None)
def test_generate_chapter_agent_entrypoint_preserves_missing_api_key_400(mock_key, client):
    pid = _create_project_with_setup(client)

    response = client.post(f"/api/v1/projects/{pid}/chapters/1/generate")

    assert response.status_code == 400
    assert response.json()["detail"] == "API key not configured"
```

The setup helper patches setup API key separately, so this test still creates setup but blocks chapter generation.

## Task 3: Implementation

- [x] Update `backend/app/schemas/chapter.py`:

```python
from typing import Any

class ChapterOut(BaseModel):
    ...
    agent_run_id: str | None = None
    control_plane: dict[str, Any] | None = None
```

- [x] Update `backend/app/api/chapters.py`:

```python
from app.services.writing_agent.api_control_plane import AgentApiToolRunResult, execute_agent_api_tool

CHAPTER_AGENT_CONTROL_PLANE_VERSION = "phase69.chapter_agent.v1"
CHAPTER_GENERATE_ENTRYPOINT = "chapter_generate"
CHAPTER_GENERATION_ERROR_STATUS_CODES = {
    "API key not configured": 400,
    "Chapter index exceeds project target chapter count": 400,
    "Setup not generated yet": 400,
    EMPTY_CHAPTER_CONTENT_ERROR: 502,
}

@router.post("/{chapter_index}/generate", response_model=ChapterOut)
async def generate_chapter(project_id: str, chapter_index: int = Path(..., ge=1), db: Session = Depends(get_db)):
    result = await execute_agent_api_tool(
        db,
        project_id=project_id,
        entrypoint=CHAPTER_GENERATE_ENTRYPOINT,
        version=CHAPTER_AGENT_CONTROL_PLANE_VERSION,
        source=CHAPTER_GENERATE_ENTRYPOINT,
        action_type="generate_chapter",
        tool_name="generate_chapter",
        goal=f"生成第{chapter_index}章正文",
        params={"chapter_index": chapter_index},
        extra_control_plane={"chapter_index": chapter_index},
    )
    _raise_if_agent_chapter_generation_failed(result)
    chapter = db.query(ChapterContent).filter(
        ChapterContent.project_id == project_id,
        ChapterContent.chapter_index == chapter_index,
    ).first()
    if not chapter:
        raise HTTPException(status_code=500, detail="Agent chapter generation completed without chapter output")
    body = _chapter_out(db, chapter)
    body["agent_run_id"] = result.run.id
    body["control_plane"] = result.control_plane
    return body
```

- [x] Add helper:

```python
def _raise_if_agent_chapter_generation_failed(result: AgentApiToolRunResult) -> None:
    if result.run.status == "success":
        return
    detail = result.run.error or "Agent chapter generation failed"
    status_code = CHAPTER_GENERATION_ERROR_STATUS_CODES.get(detail, 500)
    raise HTTPException(status_code=status_code, detail=detail)
```

## Task 4: Verification

- [x] Run focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py -q -k "test_generate_chapter or agent_entrypoint"
```

- [x] Run related T1/T2 backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_chapters.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py tests\test_athena_ontology_agent.py tests\test_athena_evolution_generation_windows.py -q
```

- [x] Static checks and secret scan:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

- [x] Write Phase69 report.
- [x] Commit and push to `main`.

## Boundaries

Do:

- migrate direct chapter generation API into Agent run;
- preserve `create_or_replace_chapter()` as the low-level tool implementation;
- preserve existing chapter response fields and add provenance metadata;
- keep validation behavior compatible.

Do not:

- migrate continuous writing start/resume yet;
- change chapter prompts or post-generation maintenance;
- rewrite task queue progress behavior;
- add frontend Agent run display in this phase.
