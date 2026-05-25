# Phase40 Agent Tool Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the first Writing Agent tool registry so existing novelv3 modules can be exposed as explicit Agent-callable capabilities instead of scattered hard-coded tool names.

**Architecture:** Add a compatibility registry beside the current Writing Agent run service. The registry describes current tools with category, module owner, schema, target type, visibility prerequisites, and report behavior; `run_service.py` will still execute tools through the existing dispatcher, but it will derive allow-lists and target metadata from the registry. Add one read-only introspection tool so the Agent can ask which tools are currently usable for a project/chapter.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic schemas, Writing Agent run service, targeted pytest.

---

## Course Correction

User clarification for this phase:

- The goal is to upgrade novelv3 into a dedicated long-memory writing Agent.
- The main engineering path is to turn existing modules into tools/capabilities that the Agent can discover, call, combine, audit, and recover from.
- Novel generation remains the diagnostic pressure test, not the center of implementation work.
- The three reference projects should inform Agent engineering patterns, especially tool registry, capability projection, result normalization, memory layers, subagent orchestration, failure handling, and trace.

Reference synthesis:

- `openclaw`: strong `ToolDescriptor`, visible/hidden tool plan, availability diagnostics, and guarded tool-result handling.
- `hermes-agent`: strong tool registry/toolset split, schema-driven argument coercion, standard tool result/error, background review, and session search.
- `openhuman`: strong tool trait, complete-vs-visible capability split, data-defined subagents, memory tree, progress/events, and explicit failure paths.

This phase implements only the first contract layer. It does not build the full autonomous planner yet.

## Current State

- `backend/app/services/writing_agent/run_service.py` owns `ALLOWED_TOOLS`, `INTERNAL_TOOLS`, `NON_BLOCKING_REPORT_TOOLS`, `_target_type_for_tool`, and a large `_execute_tool` dispatcher.
- Agent runs still require callers to pass explicit `tools` in order.
- The system has useful capabilities, but they are not discoverable or diagnosable as a tool surface.
- Current branch before this phase: `main`, clean and synced with `origin/main`.

## Scope

In scope:

- Create `backend/app/services/writing_agent/tool_registry.py`.
- Move tool metadata into descriptors.
- Add `describe_agent_tools` as a read-only internal tool.
- Refactor `run_service.py` to derive allow-list/report/target metadata from the registry.
- Add focused tests for registry uniqueness, capability visibility, and the new introspection tool.
- Update this phase report after implementation and targeted validation.

Out of scope:

- Replacing `_execute_tool` with executor objects.
- Building the full autonomous planner.
- Changing frontend UI.
- Changing database schema.
- Running full T3 verification unless targeted tests expose high-risk regression.

## Task 1: Write Failing Registry Contract Tests

**Files:**

- Create: `backend/tests/test_writing_agent_tool_registry.py`

- [x] **Step 1: Add descriptor contract test**

Create a test that imports:

```python
from app.services.writing_agent.tool_registry import (
    allowed_tool_names,
    get_agent_tool_descriptor,
    list_agent_tool_descriptors,
    non_blocking_report_tool_names,
    target_type_for_tool,
)
```

Assert:

- all descriptor names are unique;
- `generate_chapter`, `preflight_writing`, and `describe_agent_tools` exist;
- every descriptor has `category`, `module`, `description`, `input_schema["type"] == "object"`, and `output_schema["type"] == "object"`;
- `allowed_tool_names()` equals all descriptor names;
- `target_type_for_tool("describe_agent_tools") == "agent_tool_plan"`;
- `review_chapter_quality` remains non-blocking report tool.

- [x] **Step 2: Add visibility test for incomplete project**

Create a project with no setup/outline and call:

```python
build_agent_tool_plan(db_session, project.id, chapter_index=2)
```

Assert:

- `generate_setup` and `preflight_writing` are visible;
- `generate_chapter` is hidden;
- hidden diagnostics include `missing_setup`, `missing_outline_chapter`, and `missing_previous_chapter`.

- [x] **Step 3: Add visibility test for ready chapter**

Seed setup, storyline, outline chapter 2, and chapter 1 content. Call:

```python
build_agent_tool_plan(db_session, project.id, chapter_index=2)
```

Assert:

- `generate_chapter` is visible;
- `review_chapter_quality` is hidden before chapter 2 content exists;
- diagnostics can include a warning for missing world model profile but must not hide `generate_chapter` for that warning alone.

- [x] **Step 4: Verify tests fail for missing module**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py -q
```

Expected: FAIL because `app.services.writing_agent.tool_registry` does not exist yet.

## Task 2: Implement Tool Registry

**Files:**

- Create: `backend/app/services/writing_agent/tool_registry.py`

- [x] **Step 1: Add descriptor dataclass and public helpers**

Implement:

```python
@dataclass(frozen=True)
class AgentToolDescriptor:
    name: str
    module: str
    category: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    target_type: str | None
    internal: bool = False
    non_blocking_report: bool = False
    sort_key: int = 100
    availability_checks: tuple[str, ...] = ()
    warning_checks: tuple[str, ...] = ()
```

Public helpers:

- `list_agent_tool_descriptors()`
- `get_agent_tool_descriptor(name)`
- `allowed_tool_names()`
- `internal_tool_names()`
- `non_blocking_report_tool_names()`
- `target_type_for_tool(name)`
- `build_agent_tool_plan(db, project_id, chapter_index=None)`

- [x] **Step 2: Register existing tools**

Add descriptors for all current tools plus `describe_agent_tools`.

Minimum categories:

- `generation`: `generate_setup`, `generate_storyline`, `generate_outline`, `generate_chapter`, `expand_outline_window`
- `preflight`: `preflight_writing`, `describe_agent_tools`
- `athena_world_model`: world model import/analyze/proposal tools
- `review`: chapter quality/continuity/revision planning
- `revision`: revision draft/apply/expand/compress
- `maintenance`: `backfill_outline_gaps`, `seed_continuity_anchor_proposals`

- [x] **Step 3: Implement availability checks**

Supported checks:

- `project_exists`
- `setup_exists`
- `storyline_exists`
- `outline_exists`
- `outline_chapter_exists`
- `previous_chapter_exists`
- `generated_chapter_exists`
- `world_model_profile_exists`

Return diagnostics as dictionaries with:

```python
{
    "code": "missing_setup",
    "severity": "blocker",
    "message": "项目缺少已生成设定。",
    "tool_name": "generate_chapter",
}
```

For `world_model_profile_exists` on `generate_chapter`, use warning severity so writing can proceed while still exposing the missing Athena profile.

- [x] **Step 4: Verify registry tests pass**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py -q
```

Expected: PASS.

## Task 3: Wire Registry Into Run Service

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Replace scattered constants with registry-derived values**

In `run_service.py`, import:

```python
from app.services.writing_agent.tool_registry import (
    allowed_tool_names,
    build_agent_tool_plan,
    internal_tool_names,
    non_blocking_report_tool_names,
    target_type_for_tool,
)
```

Then set:

```python
ALLOWED_TOOLS = allowed_tool_names()
INTERNAL_TOOLS = internal_tool_names()
NON_BLOCKING_REPORT_TOOLS = non_blocking_report_tool_names()
```

Keep `CHAPTER_TOOL_NAME = "generate_chapter"` unchanged.

- [x] **Step 2: Add `describe_agent_tools` dispatcher branch**

In `_execute_tool`, before `preflight_writing`, add:

```python
if tool.tool_name == "describe_agent_tools":
    chapter_index = _optional_int(tool.params.get("chapter_index"))
    return build_agent_tool_plan(self.db, project_id, chapter_index=chapter_index)
```

- [x] **Step 3: Delegate target type lookup**

Replace `_target_type_for_tool` mapping body with:

```python
return target_type_for_tool(tool_name)
```

- [x] **Step 4: Add API execution test**

In `backend/tests/test_writing_agent_runs.py`, add a test that posts an Agent run with:

```json
{
  "goal": "查看当前 Agent 工具",
  "tools": [
    {"tool_name": "describe_agent_tools", "params": {"chapter_index": 1}}
  ]
}
```

Assert:

- response status is `200`;
- run status is `success`;
- step target type is `agent_tool_plan`;
- output status is `completed`;
- output includes `visible_tools`, `hidden_tools`, and `diagnostics`;
- visible tools include `generate_setup`.

- [x] **Step 5: Verify targeted run-service tests**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "tool_registry or describe_agent_tools or unsupported writing agent tool or run_and_step_persist"
```

Expected: PASS.

## Task 4: Report and Targeted Verification

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase40-agent-tool-registry.md`
- Modify: `docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`

- [x] **Step 1: Write phase report**

Report must include:

- the user correction that Agent toolization is the priority;
- reference synthesis from openclaw, hermes-agent, and openhuman;
- implemented files;
- validation level and commands;
- limitations and Phase41 recommendation.

- [x] **Step 2: Run T1 verification**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "tool_registry or describe_agent_tools or unsupported writing agent tool or run_and_step_persist"
```

Expected:

- whitespace check passes;
- secret scan returns no output;
- targeted pytest passes.

- [x] **Step 3: Commit and push**

Commit after successful T1 verification:

```powershell
git add docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md docs/superpowers/plans/long-memory-agent/2026-05-20-phase40-agent-tool-registry.md docs/superpowers/notes/long-memory-agent/2026-05-20-phase40-agent-tool-registry.md backend/app/services/writing_agent/run_service.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py
git commit -m "feat: add writing agent tool registry"
git push origin main
```

## Self-Review

- The plan directly implements the user's toolization correction.
- It avoids a large planner rewrite in this phase.
- It uses TDD for behavior changes.
- It keeps validation at T1 because this is a backend compatibility slice with no schema or frontend changes.
- It creates a clear next step: Phase41 can build autonomous tool-chain planning on top of the registry.
