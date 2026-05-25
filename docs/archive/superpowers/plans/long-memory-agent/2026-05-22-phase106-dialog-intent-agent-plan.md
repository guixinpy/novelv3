# Phase106 Dialog Intent Agent Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect natural-language dialog intent projection to a read-only Writing Agent run plan so low-detail user input can produce an auditable tool-chain plan.

**Architecture:** Add a narrow planning bridge that reuses `IntentRouter.project()` and `build_writing_agent_run_plan()`. The bridge maps matched preview dialog actions into planner intents, returns no executable side effects, and exposes projection, planner mapping, tools, and trace in one report.

**Tech Stack:** FastAPI backend service layer, SQLAlchemy session, pytest, existing Writing Agent tool registry and executor.

---

## Phase Scope

- Phase: 106
- System capability: dialog entrypoint agentization
- Novel progress: no new chapter generation in this phase
- Verification layer: T1, focused backend tests for planner/executor/intent route behavior
- Not doing: replacing Hermes dialog flow, executing the planned tools, adding front-end UI, or expanding non-preview dialog actions

## Files

- Create: `backend/app/services/writing_agent/dialog_intent_planner.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase106-dialog-intent-agent-plan.md`

## Task 1: Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Add setup-intent plan test**

Add a test that calls the future `plan_dialog_intent_agent_run` tool with a low-detail setup request:

```python
@pytest.mark.asyncio
async def test_tool_executor_handles_dialog_intent_agent_plan_for_setup(db_session):
    project = Project(name="Dialog Intent Agent Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={
                "text": "帮我创建这个都市悬疑新书的基础设定",
                "missing_items": ["setup", "storyline", "outline"],
                "completed_items": [],
                "suggested_next_step": "preview_setup",
            },
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "completed"
    assert result.output["version"] == "phase106.dialog_intent_agent_plan.v1"
    assert result.output["intent_projection"]["rule_id"] == "setup_intent"
    assert result.output["planner"]["intent_class"] == "setup_project"
    assert result.output["planner"]["mapped_from_action_type"] == "preview_setup"
    assert [tool["tool_name"] for tool in result.output["tools"]] == ["describe_agent_tools", "generate_setup"]
```

- [ ] **Step 2: Add unmatched-input no-plan test**

Add a test for non-writing chat input:

```python
@pytest.mark.asyncio
async def test_tool_executor_dialog_intent_agent_plan_returns_no_plan_for_unmatched_text(db_session):
    project = Project(name="Dialog Intent No Plan")
    db_session.add(project)
    db_session.commit()

    result = await execute_writing_agent_tool(
        WritingAgentToolContext(db=db_session, project_id=project.id, run_id="run-dialog-intent-no-plan"),
        WritingAgentToolRequest(
            tool_name="plan_dialog_intent_agent_run",
            params={"text": "今天先随便聊聊"},
        ),
    )

    assert result.handled is True
    assert result.output is not None
    assert result.output["status"] == "no_plan"
    assert result.output["tools"] == []
    assert result.output["intent_projection"]["status"] == "no_match"
    assert result.output["trace"]["reason"] == "intent_not_matched"
```

- [ ] **Step 3: Run tests and verify they fail for missing tool**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_intent_agent_plan" -q
```

Expected: fail because `plan_dialog_intent_agent_run` is not registered or handled yet.

## Task 2: Planning Bridge

**Files:**
- Create: `backend/app/services/writing_agent/dialog_intent_planner.py`

- [ ] **Step 1: Add planner bridge**

Create `plan_dialog_intent_agent_run(...)` with this behavior:

- Build `ProjectDiagnosisOut` from explicit params when provided; otherwise use `build_project_diagnosis`.
- Call `IntentRouter().project(...)`.
- If no candidate or no supported preview action, return `status="no_plan"` with empty `tools`.
- Map `preview_setup` to `setup_project`, `preview_chapter` to `continue_next_chapter`.
- Preserve unsupported matched actions as `status="blocked"` rather than guessing.
- Call `build_writing_agent_run_plan(...)` for supported mappings.
- Return `version`, `status`, `intent_projection`, `planner`, `plan`, `tools`, and `trace`.

## Task 3: Tool Registry and Executor

**Files:**
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Add tool descriptor**

Register `plan_dialog_intent_agent_run` as an internal read-only preflight tool with `target_type="agent_tool_plan"` and `non_blocking_report=True`.

- [ ] **Step 2: Add static adapter**

Add `_plan_dialog_intent_agent_run(...)` in `tool_executor.py` and include it in `_STATIC_TOOL_ADAPTERS`.

- [ ] **Step 3: Update migration tracking tests**

Add the new tool name to static adapter coverage and unhandled-internal exclusions.

## Task 4: Verification and Report

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase106-dialog-intent-agent-plan.md`

- [ ] **Step 1: Run T1 tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_planner.py -k "dialog_intent_agent_plan or plan_dialog_intent_agent_run or planner" -q
```

- [ ] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]" backend docs
```

- [ ] **Step 3: Write phase report**

Record:

- Actual changes
- Novel progress
- Fixed system gap
- Verification commands and results
- Next phase recommendation

- [ ] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend/app/services/writing_agent/dialog_intent_planner.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase106-dialog-intent-agent-plan.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase106-dialog-intent-agent-plan.md
git commit -m "feat: plan agent runs from dialog intent"
git push origin main
```
