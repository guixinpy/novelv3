# Phase41 Agent Run Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Writing Agent convert a high-level user intent into an explainable tool-chain plan, and optionally execute that plan when the caller explicitly requests auto planning.

**Architecture:** Add a deterministic planner layer on top of the Phase40 tool registry. The planner reads the current project/chapter state through `build_agent_tool_plan`, selects a bounded sequence of existing tools, records why each tool is selected or skipped, and returns a structured plan. `run_service.py` gains a read-only `plan_writing_agent_run` tool plus an explicit `input.auto_plan=true` path for empty tool lists.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic request payloads, Writing Agent tool registry, targeted pytest.

---

## Course Correction

This phase implements the user's latest direction:

- Continue prioritizing Agentization over manual chapter generation.
- First turn modules into tools, then build Agent orchestration over them.
- Absorb the engineering capabilities of `openclaw`, `hermes-agent`, and `openhuman`, but keep novelv3 specialized for long-form web novel writing.

Reference synthesis for this phase:

- `openclaw`: compact tool plans, deterministic parse before model planning, visible/hidden capability diagnostics.
- `hermes-agent`: tool registry + available tool filtering + trajectory fields + iteration budget.
- `openhuman`: progress/task-board style step state, tool whitelist, explicit failure strategies.

## Current State

- Phase40 introduced `backend/app/services/writing_agent/tool_registry.py`.
- `describe_agent_tools` exposes visible/hidden tools and diagnostics.
- Agent runs still usually require a caller to provide exact `tools` order.
- `run_service.create_run()` stores `payload.tools`; `execute_run()` receives the explicit tool list.

## Scope

In scope:

- Add `backend/app/services/writing_agent/planner.py`.
- Add a registry descriptor for `plan_writing_agent_run`.
- Add `plan_writing_agent_run` execution branch.
- Add explicit `input.auto_plan=true` support when `payload.tools` is empty.
- Add tests for planner output and auto-plan execution.
- Add a Phase41 report.

Out of scope:

- Model-based free-form planning.
- Subagent execution loops.
- Frontend changes.
- Database schema changes.
- Automatically enabling planning for all empty tool runs without `auto_plan=true`.
- Replacing the existing `_execute_tool` dispatcher.

## Planner Contract

Input:

```python
build_writing_agent_run_plan(
    db,
    project_id,
    goal,
    chapter_index=None,
    intent=None,
)
```

Output:

```python
{
    "status": "completed" | "blocked",
    "planner_version": "phase41.deterministic.v1",
    "intent_class": "continue_next_chapter" | "setup_project" | "review_chapter" | "inspect_tools",
    "goal": "...",
    "chapter_index": 2,
    "steps": [
        {
            "step_index": 1,
            "tool_name": "preflight_writing",
            "params": {"chapter_index": 2},
            "reason": "检查第2章生成前依赖。",
            "on_missing": "fallback_tool",
            "on_failure": "stop",
            "expected_output": "章节可写性检查。"
        }
    ],
    "trace": {
        "selected_tools": ["preflight_writing"],
        "rejected_tools": [{"tool_name": "generate_chapter", "reason": "..."}],
        "missing_dependencies": [{"tool_name": "generate_chapter", "code": "missing_outline_chapter"}],
        "risk_flags": []
    },
    "tools": [
        {"tool_name": "preflight_writing", "params": {"chapter_index": 2}}
    ]
}
```

## Task 1: Write Planner Tests First

**Files:**

- Create: `backend/tests/test_writing_agent_planner.py`

- [x] **Step 1: Test ready next-chapter plan**

Use `_seed_ready_project`-style local helper with setup/storyline/outline chapter 2 and generated chapter 1. Call:

```python
plan = build_writing_agent_run_plan(
    db_session,
    project.id,
    goal="继续写下一章",
    chapter_index=2,
)
```

Assert:

- `plan["status"] == "completed"`;
- `plan["intent_class"] == "continue_next_chapter"`;
- `plan["chapter_index"] == 2`;
- tool order is:
  - `describe_agent_tools`
  - `preflight_writing`
  - `generate_chapter`
  - `review_chapter_quality`
  - `review_chapter_continuity`
  - `analyze_chapter_world_model`
- generated/review/analyze follow-up steps have `post_generation is True` or equivalent structured reason.

- [x] **Step 2: Test missing outline falls back to outline expansion**

Seed setup/storyline/outline with chapter 1 only and generated chapter 1. Ask for chapter 2.

Assert tool order:

- `describe_agent_tools`
- `expand_outline_window`
- `preflight_writing`
- `generate_chapter`
- review/analyze follow-up tools

Assert `expand_outline_window.params == {"start_chapter": 2, "end_chapter": 2}`.

- [x] **Step 3: Test missing previous chapter blocks**

Seed setup/storyline/outline chapter 3 with no generated chapter 2. Ask for chapter 3.

Assert:

- `plan["status"] == "blocked"`;
- no `generate_chapter` step;
- `trace["missing_dependencies"]` includes `missing_previous_chapter`;
- `trace["risk_flags"]` includes `missing_previous_chapter`.

- [x] **Step 4: Test setup-project intent**

Create a bare project and call with `goal="创建一个都市悬疑设定"`.

Assert tool order:

- `describe_agent_tools`
- `generate_setup`

- [x] **Step 5: Verify red**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py -q
```

Expected: FAIL because planner module does not exist yet.

## Task 2: Implement Planner Module

**Files:**

- Create: `backend/app/services/writing_agent/planner.py`

- [x] **Step 1: Add intent/chapter helpers**

Implement:

- `_infer_chapter_index(db, project_id, explicit_chapter_index)`
  - explicit value wins;
  - otherwise next chapter is `max(generated chapter_index) + 1`;
  - if no generated chapters, use `1`.
- `_classify_intent(goal, chapter_index)`
  - setup words: `设定`, `开书`, `创建`, `新书` -> `setup_project`
  - review words: `审稿`, `检查`, `复查`, `问题` -> `review_chapter`
  - otherwise if chapter exists -> `continue_next_chapter`
  - fallback -> `inspect_tools`

- [x] **Step 2: Add step builders**

Implement helpers returning dictionaries:

- `_tool_step(index, tool_name, params, reason, on_missing, on_failure, expected_output, post_generation=False)`
- `_tool_request_from_step(step)` returning `{"tool_name": ..., "params": ...}`

- [x] **Step 3: Build deterministic plans**

Implement `build_writing_agent_run_plan(...)`.

Rules:

- Always start with `describe_agent_tools`.
- `setup_project`: if setup is missing, add `generate_setup`; if setup exists, return completed with rejected reason for `generate_setup`.
- `review_chapter`: add `review_chapter_quality`, `review_chapter_continuity`, and `plan_chapter_revision` only if generated chapter exists; otherwise blocked.
- `continue_next_chapter`:
  - if outline chapter is missing but `expand_outline_window` has no blockers, add `expand_outline_window`.
  - if previous chapter missing, block and do not add `generate_chapter`.
  - add `preflight_writing`;
  - add `generate_chapter` if setup, outline/expand step, and previous chapter are available;
  - add post-generation `review_chapter_quality`, `review_chapter_continuity`, and `analyze_chapter_world_model` even though they are hidden before generation, because they are expected follow-up tools.
- Populate `trace.selected_tools`, `trace.rejected_tools`, `trace.missing_dependencies`, and `trace.risk_flags`.

## Task 3: Register and Execute Planner Tool

**Files:**

- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Register `plan_writing_agent_run`**

Add descriptor:

- name: `plan_writing_agent_run`
- module: `writing_agent`
- category: `preflight`
- target_type: `agent_tool_plan`
- internal: `True`
- non_blocking_report: `True`
- availability_checks: `("project_exists",)`

- [x] **Step 2: Add registry test expectation**

Update registry contract test to assert `plan_writing_agent_run` exists and target type is `agent_tool_plan`.

- [x] **Step 3: Add execution branch**

In `_execute_tool`, add:

```python
if tool.tool_name == "plan_writing_agent_run":
    from app.services.writing_agent.planner import build_writing_agent_run_plan

    chapter_index = _optional_int(tool.params.get("chapter_index"))
    intent = str(tool.params.get("intent") or "").strip() or None
    goal = str(tool.params.get("goal") or tool.command_args or "").strip() or "规划下一步写作"
    return build_writing_agent_run_plan(self.db, project_id, goal=goal, chapter_index=chapter_index, intent=intent)
```

- [x] **Step 4: Add API test for planner tool**

Post a run with one tool:

```json
{"tool_name": "plan_writing_agent_run", "params": {"goal": "继续写下一章", "chapter_index": 2}}
```

Assert output contains `tools`, `steps`, and selected `generate_chapter`.

## Task 4: Add Explicit Auto-Plan Execution

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/api/writing_agent_runs.py`
- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Store effective tools in run input**

Add service method:

```python
def build_auto_plan_tools(self, project_id: str, payload: WritingAgentRunCreate) -> tuple[list[WritingAgentToolRequest], dict[str, Any]]:
```

Behavior:

- if `payload.tools` is not empty, return them unchanged and `{"auto_planned": False}`;
- if `payload.input.get("auto_plan") is not True`, return empty list and `{"auto_planned": False}`;
- otherwise call planner and convert `plan["tools"]` into `WritingAgentToolRequest` list.

- [x] **Step 2: Update API create flow**

In `create_agent_run`, call `build_auto_plan_tools` before `create_run`, pass effective tools to `create_run` and `execute_run`.

If changing `create_run` signature is cleaner, use:

```python
def create_run(self, project_id, payload, *, effective_tools=None, planner_output=None)
```

Store:

```python
"tools": [tool.model_dump() for tool in effective_tools],
"planner": planner_output,
```

- [x] **Step 3: Add auto-plan API test with mocked execution**

Seed ready project for chapter 2. Monkeypatch `ActionExecutionService.execute` so `generate_chapter` returns success and a trace. Post:

```json
{
  "goal": "继续写下一章",
  "input": {"auto_plan": true, "chapter_index": 2}
}
```

Assert:

- run status is success or blocked only if a post-generation report blocks by design;
- created steps include `describe_agent_tools`, `preflight_writing`, `generate_chapter`;
- run input contains `planner`.

## Task 5: Report and Verify

**Files:**

- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase41-agent-run-planner.md`
- Modify: `docs/superpowers/plans/long-memory-agent/2026-05-20-phase41-agent-run-planner.md`

- [x] **Step 1: Write report**

Include:

- what changed;
- how it advances Agentization;
- why the planner is deterministic and bounded;
- validation level and commands;
- limitations and next phase.

- [x] **Step 2: Run T1/T2 verification**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q
```

Expected: all pass, secret scan no output.

- [x] **Step 3: Commit and push**

Commit and push after verification:

```powershell
git add backend/app/services/writing_agent/planner.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/run_service.py backend/app/api/writing_agent_runs.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-20-phase41-agent-run-planner.md docs/superpowers/notes/long-memory-agent/2026-05-20-phase41-agent-run-planner.md
git commit -m "feat: add writing agent run planner"
git push origin main
```

## Self-Review

- This phase directly serves the goal: Agent can begin selecting tools from high-level user intent.
- It still avoids a full open-ended planner loop, which would be premature without stronger trace and recovery.
- It keeps auto execution explicit via `input.auto_plan=true`.
- It uses existing tools instead of inventing parallel module behavior.
