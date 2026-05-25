# Phase89 World Model Apply Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `apply_world_model_proposal_resolution` into an Agent-native guarded write adapter with a structured output contract.

**Architecture:** Keep the existing guarded apply implementation in `app.core.world_proposal_resolution_apply`. Add a thin Writing Agent adapter module that normalizes tool params, preserve `confirm_apply`, register it in `tool_executor`, and remove the legacy `run_service` branch. Tighten registry output schema so planner/Trace can inspect applied reviews, invalid decisions, confirmation state, and whether generation may continue.

**Tech Stack:** Python, Writing Agent executor, Athena world-model proposal services, pytest.

---

## Scope

Do:

- add static adapter metadata for `apply_world_model_proposal_resolution`;
- keep `confirm_apply` behavior unchanged;
- remove `missing_agent_native_adapter` from contract snapshot;
- remove `output_schema_too_generic` for this tool;
- preserve existing run-service behavior and follow-up blocking rules;
- run focused tests only.

Do not:

- change world proposal review semantics;
- change approval/reject/mark-uncertain policies;
- change frontend;
- run real model generation.

## Files

- Create: `backend/app/services/writing_agent/world_model_resolution_apply_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase89-world-model-apply-agent-adapter.md`

## Task 1: RED Tests

- [ ] **Step 1: Add executor adapter tests**

In `backend/tests/test_writing_agent_tool_executor.py`:

```python
assert "apply_world_model_proposal_resolution" in names
assert "apply_world_model_proposal_resolution" not in unhandled_internal_writing_agent_tool_names()
```

Add metadata test:

```python
def test_tool_executor_exposes_apply_world_model_proposal_resolution_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("apply_world_model_proposal_resolution")

    assert metadata == {
        "tool_name": "apply_world_model_proposal_resolution",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "write",
        "handler_name": "_apply_world_model_proposal_resolution",
    }
```

Update contract snapshot assertions:

```python
assert tools_by_name["apply_world_model_proposal_resolution"]["adapter_type"] == "static"
assert tools_by_name["apply_world_model_proposal_resolution"]["mutability"] == "guarded_write"
assert tools_by_name["apply_world_model_proposal_resolution"]["requires_confirmation"] is True
assert "missing_agent_native_adapter" not in tools_by_name["apply_world_model_proposal_resolution"]["gap_codes"]
assert "output_schema_too_generic" not in tools_by_name["apply_world_model_proposal_resolution"]["gap_codes"]
```

- [ ] **Step 2: Add registry schema test**

In `backend/tests/test_writing_agent_tool_registry.py`, add:

```python
def test_agent_tool_registry_apply_world_model_resolution_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("apply_world_model_proposal_resolution")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {
        "status",
        "profile_version",
        "before_actionable_items",
        "after_actionable_items",
        "applied_count",
        "applied_reviews",
        "invalid_decision_count",
        "invalid_decisions",
        "requires_confirmation",
        "should_generate_next_chapter",
        "recommended_actions",
    }.issubset(properties)
    assert properties["applied_reviews"]["type"] == "array"
    assert properties["requires_confirmation"]["type"] == "boolean"
```

- [ ] **Step 3: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_exposes_apply_world_model_proposal_resolution_adapter_metadata backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_apply_world_model_resolution_has_structured_output_contract -q
```

Expected: fail because the adapter and structured schema do not exist yet.

## Task 2: Implement Adapter And Schema

- [ ] **Step 1: Create adapter module**

Create `backend/app/services/writing_agent/world_model_resolution_apply_tool.py`:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def apply_world_model_proposal_resolution_tool(
    db: Session,
    project_id: str,
    *,
    decisions: object,
    confirm_apply: bool,
) -> dict[str, Any]:
    from app.core.world_proposal_resolution_apply import apply_world_model_proposal_resolution

    return apply_world_model_proposal_resolution(
        db,
        project_id,
        decisions if isinstance(decisions, list) else [],
        confirm_apply=confirm_apply,
    )
```

- [ ] **Step 2: Wire executor**

In `backend/app/services/writing_agent/tool_executor.py`:

```python
def _apply_world_model_proposal_resolution(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.world_model_resolution_apply_tool import apply_world_model_proposal_resolution_tool

    return apply_world_model_proposal_resolution_tool(
        context.db,
        context.project_id,
        decisions=tool.params.get("decisions"),
        confirm_apply=tool.params.get("confirm_apply") is True,
    )
```

Register:

```python
"apply_world_model_proposal_resolution": WritingAgentToolAdapter(
    "apply_world_model_proposal_resolution",
    _apply_world_model_proposal_resolution,
    category="athena_world_model",
    mutability="write",
),
```

- [ ] **Step 3: Remove run-service branch**

Delete the `if tool.tool_name == "apply_world_model_proposal_resolution": ...` branch from `WritingAgentRunService._execute_tool()`.

- [ ] **Step 4: Tighten output schema**

In `backend/app/services/writing_agent/tool_registry.py`, replace `_STATUS_OUTPUT` for `apply_world_model_proposal_resolution` with:

```python
output_schema=_object_schema(
    {
        "status": {"type": "string"},
        "project_id": {"type": "string"},
        "profile_version": {"type": "integer"},
        "before_actionable_items": {"type": "integer"},
        "after_actionable_items": {"type": "integer"},
        "applied_count": {"type": "integer"},
        "applied_reviews": {"type": "array"},
        "invalid_decision_count": {"type": "integer"},
        "invalid_decisions": {"type": "array"},
        "requires_confirmation": {"type": "boolean"},
        "can_auto_apply": {"type": "boolean"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_actions": {"type": "array"},
    }
)
```

## Task 3: GREEN And Regression

- [ ] **Step 1: Run focused GREEN**

Run the same command from Task 1 Step 3.

Expected: pass.

- [ ] **Step 2: Run guarded apply regressions**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "apply_world_model_proposal_resolution" -q
```

Expected: pass.

- [ ] **Step 3: Run related T1 slice**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py -k "apply_world_model_proposal_resolution or inspect_agent_tool_contracts" -q
```

Expected: pass.

## Task 4: Report, T0, Commit

- [ ] **Step 1: Write report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-21-phase89-world-model-apply-agent-adapter.md`.

- [ ] **Step 2: T0 checks**

Run:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected:

- `git diff --check` exits `0`;
- `rg` exits `1` with no output.

- [ ] **Step 3: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/world_model_resolution_apply_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/run_service.py backend/app/services/writing_agent/tool_registry.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-21-phase89-world-model-apply-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-21-phase89-world-model-apply-agent-adapter.md
git commit -m "feat: adapt world proposal apply as agent tool"
git push origin main
```

