# Phase 3 Agent Run Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first thin Writing Agent run record so longform generation can be planned, executed, inspected, and quality-gated without replacing existing generation APIs.

**Architecture:** Phase 3 introduces `WritingAgentRun` and `WritingAgentStep` as durable orchestration records. Existing setup/storyline/outline/chapter generation stays in place and is called through a small Agent service that records steps, model trace links, chapter-length decisions, and Athena/world-model proposal diagnostics.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite/Alembic, existing model-call trace APIs, existing action execution service, pytest.

---

## Phase Metadata

- **Phase:** 3
- **Date:** 2026-05-18
- **Verification Tier:** T1 for model/API tests; T2 for one runtime dogfood chapter if the local backend and model key are available.
- **Primary Output:** A minimal backend Agent run API plus a Phase 3 report under `docs/superpowers/notes/long-memory-agent/`.
- **Dogfood Output:** Generate Chapter 2 of `《雾港回声》` only through the new Agent run path, not through direct chapter API calls.
- **Secret Handling:** Do not write API keys to docs, commits, or `.env`. Use runtime environment variables only.

## Phase 3 Success Criteria

- `WritingAgentRun` persists a user goal, status, input, output, error, timestamps, and optional links to background task/dialog/message ids.
- `WritingAgentStep` persists each tool call with `tool_name`, status, input/output/error, optional trace id, target type/id, and chapter index.
- New API can create/list/read/cancel Agent runs under `/api/v1/projects/{project_id}/agent-runs`.
- A run can execute at least one tool step by reusing existing generation paths, not duplicating them.
- Chapter tool steps record the generated `chapter_index`, `chapter_id`, `trace_id`, `chapter_word_target` decision, and Athena proposal queue diagnostic.
- Over/under target chapter length is visible in the Agent run output and does not pass silently.
- Empty Athena proposal queue/profile state is visible in the Agent run output and does not pass silently.
- Phase 3 report records implementation, verification, dogfood status, issues found, and next phase advice.

## Explicit Non-Goals

- Do not build a full autonomous planner.
- Do not replace Hermes chat or the existing writing scheduler.
- Do not change Athena/world-model persistence behavior in this phase.
- Do not add a new top-level frontend workspace.
- Do not introduce Celery, LangGraph, external queues, or a dependency on reference Agent projects.
- Do not rewrite setup/storyline/outline/chapter APIs.

## Files

- Create: `backend/app/models/writing_agent.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/writing_agent.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/writing_agent/__init__.py`
- Create: `backend/app/services/writing_agent/run_service.py`
- Create: `backend/app/api/writing_agent_runs.py`
- Modify: `backend/app/main.py`
- Create: `backend/alembic/versions/20260518_add_writing_agent_runs.py`
- Create: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase3-agent-run-trace.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase3-agent-run-trace.md`

## Existing Code To Reuse

- `backend/app/services/actions/action_execution_service.py`
  - Reuse `ActionExecutionService.execute()` for `generate_setup`, `generate_storyline`, `generate_outline`, and `generate_chapter`.
- `backend/app/api/model_call_traces.py`
  - Keep model-call trace inspection in the existing route.
- `backend/app/models/ai_model_call_trace.py`
  - Store references from Agent steps to model-call trace ids; do not alter trace table shape.
- `backend/app/api/athena_evolution.py`
  - Use proposal review queue behavior as a diagnostic source, not as a data model dependency.
- `backend/app/core/chapter_target.py`
  - Reuse target range semantics from existing chapter trace metadata instead of inventing a new length formula.

## Task 1: Add Persistent Agent Run Models

**Files:**
- Create: `backend/app/models/writing_agent.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/20260518_add_writing_agent_runs.py`
- Test: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write the failing model persistence test**

Add a test that imports the new models, creates a run and one step, commits them, and verifies project-scoped retrieval.

Expected test name:

```python
def test_writing_agent_run_and_step_persist(client, db_session):
    ...
```

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_writing_agent_run_and_step_persist -q
```

Expected: fails because the models do not exist.

- [ ] **Step 2: Create SQLAlchemy models**

Implement `WritingAgentRun` and `WritingAgentStep` in `backend/app/models/writing_agent.py`.

Required fields:

```python
class WritingAgentRun(Base):
    __tablename__ = "writing_agent_runs"

    id: str
    project_id: str
    goal: str
    status: str
    entrypoint: str
    input: dict
    output: dict | None
    error: str | None
    background_task_id: str | None
    dialog_id: str | None
    request_message_id: str | None
    response_message_id: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime
```

```python
class WritingAgentStep(Base):
    __tablename__ = "writing_agent_steps"

    id: str
    run_id: str
    project_id: str
    step_index: int
    tool_name: str
    status: str
    input: dict
    output: dict | None
    error: str | None
    trace_id: str | None
    background_task_id: str | None
    target_type: str | None
    target_id: str | None
    chapter_index: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
```

Add indexes for:

- `(project_id, created_at, id)` on runs.
- `(run_id, step_index, id)` on steps.
- `(project_id, tool_name, created_at, id)` on steps.

- [ ] **Step 3: Export models**

Add to `backend/app/models/__init__.py`:

```python
from .writing_agent import WritingAgentRun, WritingAgentStep
```

- [ ] **Step 4: Add migration**

Create `backend/alembic/versions/20260518_add_writing_agent_runs.py` with `upgrade()` creating both tables and indexes, and `downgrade()` dropping them.

- [ ] **Step 5: Run model persistence test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_writing_agent_run_and_step_persist -q
```

Expected: pass.

## Task 2: Add Schemas And Project-Scoped API

**Files:**
- Create: `backend/app/schemas/writing_agent.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/app/api/writing_agent_runs.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing API tests**

Add tests for:

```python
def test_create_agent_run_records_steps_and_returns_detail(client, db_session, monkeypatch):
    ...

def test_agent_run_list_and_detail_are_project_scoped(client, db_session):
    ...

def test_cancel_agent_run_marks_pending_or_running_run_cancelled(client, db_session):
    ...
```

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: API route not found or imports missing.

- [ ] **Step 2: Define Pydantic schemas**

Create request/response schemas:

```python
class WritingAgentToolRequest(BaseModel):
    tool_name: str
    command_args: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)

class WritingAgentRunCreate(BaseModel):
    goal: str
    entrypoint: str = "api"
    tools: list[WritingAgentToolRequest] = Field(default_factory=list)
    input: dict[str, Any] = Field(default_factory=dict)

class WritingAgentStepOut(BaseModel):
    ...

class WritingAgentRunListItem(BaseModel):
    ...

class WritingAgentRunDetail(WritingAgentRunListItem):
    steps: list[WritingAgentStepOut] = Field(default_factory=list)
```

Use `ConfigDict(from_attributes=True)` for model-backed outputs.

- [ ] **Step 3: Add service skeleton**

Create `backend/app/services/writing_agent/run_service.py` with methods:

```python
class WritingAgentRunService:
    def create_run(...)
    async def execute_run(...)
    def list_runs(...)
    def get_run_detail(...)
    def cancel_run(...)
```

At this task, `execute_run` may execute tools sequentially using a helper method that will be expanded in Task 3.

- [ ] **Step 4: Add API route**

Create `backend/app/api/writing_agent_runs.py` with:

- `POST /api/v1/projects/{project_id}/agent-runs`
- `GET /api/v1/projects/{project_id}/agent-runs`
- `GET /api/v1/projects/{project_id}/agent-runs/{run_id}`
- `POST /api/v1/projects/{project_id}/agent-runs/{run_id}/cancel`

Register the router in `backend/app/main.py`.

- [ ] **Step 5: Run API tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: tests written so far pass.

## Task 3: Record Tool Steps, Trace Links, And Diagnostics

**Files:**
- Modify: `backend/app/services/writing_agent/run_service.py`
- Test: `backend/tests/test_writing_agent_runs.py`

- [ ] **Step 1: Write failing step execution tests**

Add tests for:

```python
async def test_agent_run_records_successful_tool_step_with_trace_id(client, db_session, monkeypatch):
    ...

async def test_agent_run_stops_after_failed_tool_step(client, db_session, monkeypatch):
    ...

async def test_agent_run_records_chapter_length_and_world_model_diagnostics(client, db_session, monkeypatch):
    ...
```

The tests should monkeypatch `ActionExecutionService.execute()` so they are deterministic and do not call an external model.

- [ ] **Step 2: Implement sequential tool execution**

For each requested tool:

1. Create a `WritingAgentStep` with `status="running"`.
2. Call `ActionExecutionService.execute(tool_name, project_id, command_args=..., action_params=...)`.
3. If result status is success, mark the step success and save output.
4. If result status is failed, mark the step failed, mark the run failed, and stop.
5. Save `trace_id`, `chapter_index`, `target_type`, and target ids when available.

Allowed tools in Phase 3:

- `generate_setup`
- `generate_storyline`
- `generate_outline`
- `generate_chapter`

Reject unknown tools with a failed run and failed step.

- [ ] **Step 3: Add chapter-length decision extraction**

When a step output includes `trace_id` for a chapter, load the trace metadata and write this summary to `step.output["chapter_length_decision"]`:

```json
{
  "status": "within|under|over|unknown",
  "decision": "accept|accept_with_warning|requires_revision",
  "actual_word_count": 3735,
  "target_min_word_count": 1700,
  "target_average_word_count": 2000,
  "target_max_word_count": 2300
}
```

Decision rule for Phase 3:

- `within` -> `accept`
- `under` or `over` -> `accept_with_warning`
- missing metadata -> `requires_revision`

- [ ] **Step 4: Add Athena proposal queue diagnostic**

After a successful `generate_chapter` step, query the proposal review queue using existing database/core/API helpers where feasible. Store this summary:

```json
{
  "status": "ready|missing|empty|unknown",
  "profile_version": null,
  "total_items": 0,
  "reason": "missing_profile|empty_queue|available|diagnostic_failed"
}
```

Phase 3 only records this diagnostic. It does not repair Athena proposal generation.

- [ ] **Step 5: Run service tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q
```

Expected: pass.

## Task 4: Runtime Dogfood Chapter 2 Through Agent Run

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-18-phase3-agent-run-trace.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase3-agent-run-trace.md`

- [ ] **Step 1: Run targeted tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing.py tests\test_chapters.py::test_generate_chapter_records_model_call_trace -q
```

Expected: pass.

- [ ] **Step 2: Run diff check**

Run:

```powershell
git diff --check
```

Expected: exit code 0.

- [ ] **Step 3: Start or reuse backend**

Use existing local backend if healthy. Otherwise start on an available port with runtime-only `DEEPSEEK_API_KEY`.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/api/v1/health
```

Expected: `status=ok`.

- [ ] **Step 4: Create Agent run for Chapter 2**

Use project id `25fa2b20-5b9f-473b-918b-f4ea491cbb60` and call:

```powershell
$body = @{
  goal = '通过 Writing Agent 生成《雾港回声》第2章，要求承接第1章，正文不少于2000字，并记录长度门禁和Athena提案队列诊断。'
  entrypoint = 'api'
  tools = @(
    @{
      tool_name = 'generate_chapter'
      command_args = '请生成《雾港回声》第2章。承接第1章雾港、记忆异常、林深调查与雾晶线索，保持都市悬疑轻科幻风格，正文不少于2000字。'
      params = @{ chapter_index = 2 }
    }
  )
} | ConvertTo-Json -Depth 10
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8001/api/v1/projects/25fa2b20-5b9f-473b-918b-f4ea491cbb60/agent-runs' -ContentType 'application/json' -Body $body
```

Expected: run status is `success` if generation succeeds, step output includes `trace_id`, chapter length decision, and Athena proposal queue diagnostic.

- [ ] **Step 5: Inspect run detail and chapter**

Run:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/projects/25fa2b20-5b9f-473b-918b-f4ea491cbb60/agent-runs/<run_id>'
Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/projects/25fa2b20-5b9f-473b-918b-f4ea491cbb60/chapters/2'
```

Expected: chapter 2 exists as prose and the Agent run explains how it was produced.

- [ ] **Step 6: Write Phase 3 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-18-phase3-agent-run-trace.md` with:

```markdown
# Phase 3 Agent Run Trace

## Runtime
## Implementation
## Dogfood Novel Progress
## Agent Run Evidence
## Chapter 2 Metrics
## Quality Review
## Issues Found
## Issues Fixed
## Verification
## Next Phase Recommendation
```

- [ ] **Step 7: Update this plan completion notes**

Add:

```markdown
## Phase 3 Completion Notes
## Actual Completed Work
## Novel Progress
## Issues Found
## Issues Fixed
## Verification
## Next Phase Recommendation
```

## Task 5: Commit Phase 3

**Files:**
- All files changed in this phase.

- [ ] **Step 1: Secret scan**

Run:

```powershell
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references
```

Expected: no output.

- [ ] **Step 2: Status check**

Run:

```powershell
git status --short --branch
```

Expected: only Phase 3 files are modified or untracked.

- [ ] **Step 3: Commit**

Suggested split:

```powershell
git add backend
git commit -m "feat: add writing agent run trace"
git add docs/superpowers/plans/long-memory-agent/2026-05-18-phase3-agent-run-trace.md docs/superpowers/notes/long-memory-agent/2026-05-18-phase3-agent-run-trace.md
git commit -m "docs: record long memory agent phase 3"
```

Expected: commits succeed.

## Self-Review

- Spec coverage: This plan advances Agent orchestration, traceability, quality gates, and dogfood-driven generation while preserving existing APIs.
- Placeholder scan: No `TBD` or unresolved task placeholders are intentionally left.
- Scope check: Frontend is explicitly deferred because the backend API contract needs to stabilize first.

## Phase 3 Completion Notes

Phase 3 completed the first thin Writing Agent run trace implementation and used it to generate Chapter 2 of `《雾港回声》`.

One local runtime caveat was found: `data/mozhou.db` has stale Alembic revision metadata even though later tables already exist. To avoid risky duplicate migrations against dogfood data, the local runtime created only the two new Agent tables via SQLAlchemy `create(checkfirst=True)`. The committed migration remains available for fresh or correctly stamped databases.

## Actual Completed Work

- Added `WritingAgentRun` and `WritingAgentStep` SQLAlchemy models.
- Added Alembic migration `20260518_add_writing_agent_runs`.
- Added `writing_agent` schemas.
- Added `WritingAgentRunService`.
- Added `/api/v1/projects/{project_id}/agent-runs` API routes.
- Registered the new router in FastAPI.
- Added `backend/tests/test_writing_agent_runs.py`.
- Reused existing `ActionExecutionService` instead of duplicating generation logic.
- Recorded tool step output, model trace id, target id, chapter index, length decision, and world-model proposal diagnostics.

## Novel Progress

- Novel: `《雾港回声》`.
- Dogfood project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.
- Generated chapters: `2 / 600`.
- Chapter 2 was generated through Agent run id `78894cc3-d7f3-4d4e-8179-e8e461f38954`.
- Chapter 2 trace id: `08fd0a3d-6c2c-4d54-993c-094af134be9b`.
- Chapter 2 word count: `3511`.

## Issues Found

- Both generated chapters exceed the configured target range.
- Chapter 2 title is generic: `第2章`.
- Athena proposal review queue remains empty because the project has no current world-model profile.
- Local dogfood DB migration metadata is stale.

## Issues Fixed

- Agent tool execution is now durable and inspectable.
- Chapter length drift no longer passes silently through the Agent path.
- Missing world-model proposal state no longer passes silently through the Agent path.
- Chapter 2 generation is now tied to an Agent run and ordered tool step.

## Verification

- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q` -> `7 passed`.
- `.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing.py tests\test_chapters.py::test_generate_chapter_records_model_call_trace -q` -> `36 passed`.
- `git diff --check` -> exit code `0`.
- Runtime backend health on `http://127.0.0.1:8001/api/v1/health` -> `{"status":"ok"}`.
- Runtime Agent run generated Chapter 2 successfully.

## Next Phase Recommendation

Phase 4 should make Agent gates actionable before generating Chapter 3:

- Add Agent preflight readiness checks.
- Initialize/import Athena world-model profile for `《雾港回声》`.
- Turn length warnings into revise/split/stop decisions.
- Improve semantic chapter title generation or extraction.
