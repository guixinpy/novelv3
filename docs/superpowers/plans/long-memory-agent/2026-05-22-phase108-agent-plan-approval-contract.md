# Phase108 Agent Plan Approval Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only approval contract preview for Writing Agent plans so write steps can be reviewed and hash-bound before later execution phases.

**Architecture:** Phase107 already gave every plan and step stable metadata. Phase108 adds a small approval-contract builder that reads a plan, extracts write or guarded-write steps, normalizes the confirmable payload, and returns a deterministic hash without executing anything. Dialog-intent planning will include this preview so conversation-driven Agent plans expose their safety boundary immediately.

**Tech Stack:** FastAPI backend service layer, SQLAlchemy test fixtures, pytest, existing Writing Agent tool registry/executor.

---

## Phase Scope

- Phase number: 108.
- Goal alignment: turns module tools into safer Agent-callable capabilities by separating plan, approval preview, and execution.
- Novel progress: no new chapter generation in this phase; this is control-plane infrastructure needed before autonomous generation can safely run longer chains.
- Verification level: T1. The change is local to Writing Agent planning and static adapters, so targeted backend tests plus diff/secret hygiene are sufficient.
- Not doing:
  - No runtime approval enforcement.
  - No automatic tool execution.
  - No database schema changes.
  - No frontend UI work.
  - No API key or model invocation.

## Files

- Create: `backend/app/services/writing_agent/approval_contract.py`
  - Build deterministic read-only approval contract previews from plan dictionaries.
- Modify: `backend/app/services/writing_agent/planner.py`
  - Attach approval contract to base plans.
- Modify: `backend/app/services/writing_agent/dialog_intent_planner.py`
  - Attach the same contract to dialog-originated plans.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `preview_agent_plan_approval_contract`.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add static adapter for `preview_agent_plan_approval_contract`.
- Modify/Create tests:
  - `backend/tests/test_writing_agent_approval_contract.py`
  - `backend/tests/test_writing_agent_planner.py`
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_tool_registry.py`
- Create final report: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase108-agent-plan-approval-contract.md`

## Task 1: Approval Contract Builder

**Files:**
- Create: `backend/app/services/writing_agent/approval_contract.py`
- Test: `backend/tests/test_writing_agent_approval_contract.py`

- [ ] **Step 1: Write failing tests**

```python
from app.services.writing_agent.approval_contract import build_agent_plan_approval_contract


def test_approval_contract_requires_confirmation_for_write_steps():
    plan = {
        "trace": {"plan_id": "plan:abc", "source_projection_id": "projection:1", "planner_version": "phase53.context_gate.v1"},
        "steps": [
            {"step_index": 1, "step_id": "step:read", "tool_name": "describe_agent_tools", "params": {}, "mutability": "read", "requires_confirmation": False},
            {"step_index": 2, "step_id": "step:write", "tool_name": "generate_chapter", "params": {"chapter_index": 2}, "mutability": "write", "requires_confirmation": True, "reason": "生成第2章。"},
        ],
    }

    contract = build_agent_plan_approval_contract(plan)

    assert contract["status"] == "requires_confirmation"
    assert contract["plan_id"] == "plan:abc"
    assert contract["source_projection_id"] == "projection:1"
    assert contract["write_step_count"] == 1
    assert contract["write_steps"][0]["step_id"] == "step:write"
    assert contract["approval"]["required"] is True
    assert contract["approval"]["approval_contract_hash"].startswith("approval:")
    assert contract["approval"]["confirmation_param"] == "approval_contract_hash"


def test_approval_contract_is_not_required_for_read_only_plan():
    plan = {
        "trace": {"plan_id": "plan:read", "source_projection_id": None, "planner_version": "phase53.context_gate.v1"},
        "steps": [
            {"step_index": 1, "step_id": "step:read", "tool_name": "review_chapter_quality", "params": {"chapter_index": 2}, "mutability": "read", "requires_confirmation": False},
        ],
    }

    contract = build_agent_plan_approval_contract(plan)

    assert contract["status"] == "not_required"
    assert contract["write_steps"] == []
    assert contract["approval"]["required"] is False
    assert contract["approval"]["approval_contract_hash"].startswith("approval:")
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -q
```

Expected: fail because `approval_contract.py` does not exist yet.

- [ ] **Step 3: Implement minimal builder**

Create a deterministic builder that:

- Accepts a plan dict.
- Reads `trace.plan_id`, `trace.source_projection_id`, and `trace.planner_version`.
- Selects steps where `requires_confirmation is True` or `mutability` is `write` / `guarded_write`.
- Builds a normalized payload with plan id and selected step details.
- Hashes normalized JSON with sorted keys.
- Returns `status`, `version`, `plan_id`, `source_projection_id`, `write_step_count`, `write_steps`, `approval`, and `trace`.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -q
```

Expected: pass.

## Task 2: Planner and Dialog Integration

**Files:**
- Modify: `backend/app/services/writing_agent/planner.py`
- Modify: `backend/app/services/writing_agent/dialog_intent_planner.py`
- Test: `backend/tests/test_writing_agent_planner.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Write failing assertions**

Add assertions that:

- `build_writing_agent_run_plan()` returns `approval_contract`.
- Continue-next-chapter plans require confirmation for write steps.
- Review-only plans return `not_required`.
- `plan_dialog_intent_agent_run` output includes the same contract and the contract `plan_id` equals the planner `plan_id`.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -k "ready_next_chapter or review or dialog_intent_agent_plan_for_chapter" -q
```

Expected: fail on missing `approval_contract`.

- [ ] **Step 3: Attach approval contract**

Import `build_agent_plan_approval_contract` in planner and dialog planner. Add the contract to returned plan dictionaries after steps/tools are built. Preserve all existing fields and execution semantics.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py -k "ready_next_chapter or review or dialog_intent_agent_plan_for_chapter" -q
```

Expected: pass.

## Task 3: Tool Registry and Static Adapter

**Files:**
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Test: `backend/tests/test_writing_agent_tool_registry.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Write failing tests**

Add tests that:

- `preview_agent_plan_approval_contract` exists in the registry, is internal, read-only, non-blocking, and targets `agent_plan_approval_contract`.
- Static adapter names include it.
- Unhandled internal migration tracking does not include it.
- Executing the tool with a simple plan returns the same contract preview.

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "approval_contract or static_adapter_names or unhandled_internal" -q
```

Expected: fail because descriptor and adapter are missing.

- [ ] **Step 3: Register descriptor and adapter**

Add descriptor near other preflight planning tools. Add executor handler that accepts `tool.params["plan"]` and returns `build_agent_plan_approval_contract(plan)`. If plan is missing or invalid, return the builder's invalid-plan response.

- [ ] **Step 4: Run tests and verify GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "approval_contract or static_adapter_names or unhandled_internal" -q
```

Expected: pass.

## Task 4: T1 Verification, Report, Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase108-agent-plan-approval-contract.md`

- [ ] **Step 1: Run T1 module tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -q
```

Expected: pass.

- [ ] **Step 2: Run hygiene checks**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: no whitespace errors and no active secret matches.

- [ ] **Step 3: Write phase report**

Report must include:

- Actual changes.
- Why no novel chapter was generated.
- Subagent/reference review summary.
- Verification commands and results.
- Next phase recommendation.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent backend/tests docs/superpowers/plans/long-memory-agent/2026-05-22-phase108-agent-plan-approval-contract.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase108-agent-plan-approval-contract.md
git commit -m "feat: preview agent plan approval contracts"
git push
```

Expected: branch `main` remains aligned with `origin/main`.
