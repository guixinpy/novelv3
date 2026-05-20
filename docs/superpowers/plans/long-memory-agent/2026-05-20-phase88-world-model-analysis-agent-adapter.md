# Phase88 World Model Analysis Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `analyze_chapter_world_model` into an Agent-native static adapter so `generate_chapter.recommended_next_tools` points to an executor-backed post-generation tool chain.

**Architecture:** Move the `analyze_chapter_world_model` execution branch out of `WritingAgentRunService._execute_tool()` into a focused adapter module. Preserve same-run duplicate-analysis skip behavior by passing `run_id` from `WritingAgentToolContext`.

**Tech Stack:** Python, Writing Agent executor, Athena world-model service, pytest.

---

## Scope

Do:

- add static adapter metadata for `analyze_chapter_world_model`;
- remove `missing_agent_native_adapter` for this tool in contract snapshots;
- preserve existing direct analysis behavior;
- preserve same-run skip behavior when `generate_chapter` already returned `athena_analysis`.

Do not:

- change Athena extraction logic;
- change proposal resolution behavior;
- change frontend;
- run real model generation.

## Files

- Create: `backend/app/services/writing_agent/world_model_analysis_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify if needed: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase88-world-model-analysis-agent-adapter.md`

## Task 1: RED Tests

- [ ] **Step 1: Add executor metadata assertions**

In `backend/tests/test_writing_agent_tool_executor.py`, assert:

```python
assert "analyze_chapter_world_model" in names
```

Add a metadata test:

```python
def test_tool_executor_exposes_analyze_chapter_world_model_adapter_metadata():
    metadata = writing_agent_tool_adapter_metadata("analyze_chapter_world_model")

    assert metadata == {
        "tool_name": "analyze_chapter_world_model",
        "adapter_type": "static",
        "category": "athena_world_model",
        "mutability": "write",
        "handler_name": "_analyze_chapter_world_model",
    }
```

Update unhandled internal migration tracking:

```python
assert "analyze_chapter_world_model" not in names
```

Update contract snapshot test:

```python
assert tools_by_name["analyze_chapter_world_model"]["adapter_type"] == "static"
assert "missing_agent_native_adapter" not in tools_by_name["analyze_chapter_world_model"]["gap_codes"]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: fail because no static adapter exists.

## Task 2: Adapter Module

- [ ] **Step 1: Create `world_model_analysis_tool.py`**

Create a module with:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import WritingAgentStep


def analyze_chapter_world_model_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    run_id: str | None = None,
) -> dict[str, Any]:
    existing_analysis = _same_run_completed_chapter_analysis(
        db,
        run_id=run_id,
        project_id=project_id,
        chapter_index=chapter_index,
    )
    if existing_analysis is not None:
        analysis = existing_analysis["analysis"]
        return {
            "status": "skipped",
            "reason": "chapter_already_analyzed_in_run",
            "chapter_index": chapter_index,
            "source_step_id": existing_analysis["source_step_id"],
            "proposal_bundle_id": analysis.get("proposal_bundle_id"),
            "created": analysis.get("created", {"proposal_items": 0}),
            "updated": analysis.get("updated", {"proposal_items": 0}),
        }

    from app.core.athena_longform import analyze_chapter_to_world_proposals

    return analyze_chapter_to_world_proposals(db=db, project_id=project_id, chapter_index=chapter_index)
```

Move or duplicate the existing same-run lookup logic from `run_service.py` into this module. The module must not import `run_service.py`.

- [ ] **Step 2: Wire executor**

In `tool_executor.py`:

```python
def _analyze_chapter_world_model(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.world_model_analysis_tool import analyze_chapter_world_model_tool

    chapter_index = int(tool.params.get("chapter_index") or 1)
    return analyze_chapter_world_model_tool(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        run_id=context.run_id,
    )
```

Register static adapter with category `athena_world_model`, mutability `write`.

- [ ] **Step 3: Remove run-service branch**

Delete `if tool.tool_name == "analyze_chapter_world_model": ...` from `WritingAgentRunService._execute_tool()`.

If `_same_run_completed_chapter_analysis` becomes unused in `run_service.py`, remove it from that file.

## Task 3: GREEN And Regression

- [ ] **Step 1: Run focused executor tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_lists_unhandled_internal_tools_for_migration_tracking backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: pass.

- [ ] **Step 2: Run world-model Agent regression**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py::test_agent_analyze_chapter_world_model_records_proposal_output backend/tests/test_writing_agent_runs.py::test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter -q
```

Expected: pass.

- [ ] **Step 3: Run related T1 slice**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "analyze_chapter_world_model or inspect_agent_tool_contracts" -q
```

Expected: pass.

## Task 4: Report, T0, Commit

- [ ] **Step 1: Write report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase88-world-model-analysis-agent-adapter.md`.

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
git add backend/app/services/writing_agent/world_model_analysis_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-20-phase88-world-model-analysis-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-20-phase88-world-model-analysis-agent-adapter.md
git commit -m "feat: adapt chapter world analysis as agent tool"
git push origin main
```

