# Phase107 Agent Plan Step Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable, auditable metadata to Writing Agent plans so future execution, approval, and Trace layers can reason about each planned step without re-deriving tool risk.

**Architecture:** Extend the existing planner output shape instead of replacing it. Add tool descriptor mutability as registry metadata, then have `planner.py` enrich each step and tool request with `plan_id`, `step_id`, `source_projection_id`, `mutability`, and conservative `requires_confirmation`.

**Tech Stack:** Python backend service layer, existing Writing Agent tool registry/planner/executor, pytest.

---

## Phase Scope

- Phase: 107
- System capability: Agent plan auditability and approval-readiness
- Novel progress: no new chapter generation in this phase
- Verification layer: T1, focused backend tests for planner and dialog intent planner
- Not doing: executing approval gates, changing runtime execution semantics, adding UI, or introducing a full DAG scheduler

## Files

- Modify: `backend/app/services/writing_agent/tool_contracts.py`
- Modify: `backend/app/services/writing_agent/planner.py`
- Modify: `backend/app/services/writing_agent/dialog_intent_planner.py`
- Modify: `backend/tests/test_writing_agent_planner.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase107-agent-plan-step-metadata.md`

## Task 1: Failing Tests

**Files:**
- Modify: `backend/tests/test_writing_agent_planner.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Add planner metadata assertions**

Update `test_planner_builds_ready_next_chapter_tool_chain` to assert:

```python
assert plan["trace"]["plan_id"].startswith("plan:")
first_step = plan["steps"][0]
generate_step = next(step for step in plan["steps"] if step["tool_name"] == "generate_chapter")
assert first_step["step_id"].startswith("step:")
assert first_step["plan_id"] == plan["trace"]["plan_id"]
assert first_step["source_projection_id"] is None
assert first_step["mutability"] == "read"
assert first_step["requires_confirmation"] is False
assert generate_step["mutability"] == "write"
assert generate_step["requires_confirmation"] is True
assert generate_request["planner"]["step_id"] == generate_step["step_id"]
assert generate_request["planner"]["mutability"] == "write"
assert generate_request["planner"]["requires_confirmation"] is True
```

- [ ] **Step 2: Add dialog-source metadata assertions**

Update `test_tool_executor_handles_dialog_intent_agent_plan_for_chapter` to assert:

```python
projection_id = result.output["intent_projection"]["trace"]["projection_id"]
plan = result.output["plan"]
assert result.output["planner"]["plan_id"] == plan["trace"]["plan_id"]
assert plan["trace"]["source_projection_id"] == projection_id
assert all(step["source_projection_id"] == projection_id for step in plan["steps"])
```

- [ ] **Step 3: Run red tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -k "ready_next_chapter_tool_chain or dialog_intent_agent_plan_for_chapter" -q
```

Expected: fail because current plans do not expose these metadata fields.

## Task 2: Contract Mutability Metadata

**Files:**
- Modify: `backend/app/services/writing_agent/tool_contracts.py`

- [ ] **Step 1: Expose execution metadata helper**

Reuse the existing tool-contract mutability classification by adding a public helper:

```python
def agent_tool_execution_metadata(descriptor, adapter_metadata=None) -> dict[str, Any]:
    ...
```

The helper should return `mutability` and conservative `requires_confirmation`. Phase107 must not change executor behavior based on this metadata.

## Task 3: Planner Step Metadata

**Files:**
- Modify: `backend/app/services/writing_agent/planner.py`

- [ ] **Step 1: Extend planner signature**

Add optional keyword args:

```python
source_projection_id: str | None = None
source_plan_id: str | None = None
```

- [ ] **Step 2: Create plan id and enrich trace**

Create deterministic `plan_id` and store:

```python
trace["plan_id"] = plan_id
trace["source_projection_id"] = source_projection_id
```

- [ ] **Step 3: Enrich each step**

Add to `_append_step()` output:

- `plan_id`
- `step_id`
- `source_projection_id`
- `mutability`
- `requires_confirmation`

Use `get_agent_tool_descriptor(tool_name)` for mutability. Conservative rule: `requires_confirmation` is true for write tools and false for read tools.

- [ ] **Step 4: Include metadata in tool requests**

Add the same metadata to `request["planner"]` in `_tool_request_from_step()`.

## Task 4: Dialog Intent Source Propagation

**Files:**
- Modify: `backend/app/services/writing_agent/dialog_intent_planner.py`

- [ ] **Step 1: Compute plan id before planner call**

Compute the existing deterministic dialog `plan_id` before calling `build_writing_agent_run_plan()`.

- [ ] **Step 2: Pass source ids**

Pass:

```python
source_projection_id=projection_id
source_plan_id=plan_id
```

Ensure returned `planner.plan_id` and `plan.trace.plan_id` match.

## Task 5: Verification and Report

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase107-agent-plan-step-metadata.md`

- [ ] **Step 1: Run T1 tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -k "planner or dialog_intent_agent_plan or plan_dialog_intent_agent_run" -q
```

- [ ] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [ ] **Step 3: Write report**

Record actual changes, subagent feedback, verification evidence, novel progress, and next phase recommendation.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend/app/services/writing_agent/tool_contracts.py backend/app/services/writing_agent/planner.py backend/app/services/writing_agent/dialog_intent_planner.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase107-agent-plan-step-metadata.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase107-agent-plan-step-metadata.md
git commit -m "feat: add agent plan step metadata"
git push origin main
```
