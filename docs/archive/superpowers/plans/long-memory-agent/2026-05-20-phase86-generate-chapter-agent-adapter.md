# Phase86 Generate Chapter Agent Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `generate_chapter` from a Writing Agent legacy special case into an Agent-native tool adapter without changing the chapter generation behavior.

**Architecture:** Move the chapter-generation tool execution logic out of `WritingAgentRunService._execute_tool()` and into a small dedicated tool module. Register `generate_chapter` in the static Writing Agent executor so `inspect_agent_tool_contracts` no longer reports `missing_agent_native_adapter` for the core generation tool. Keep run-service step enrichment, target resolution, Trace envelope, and API behavior unchanged.

**Tech Stack:** Python, FastAPI service layer, SQLAlchemy session, pytest.

---

## Scope

This phase is a migration slice, not a new generation engine.

Do:

- add an Agent-native static adapter for `generate_chapter`;
- preserve existing continuity and length-feedback injection;
- preserve existing `ActionExecutionService(...).execute("generate_chapter", ...)` behavior;
- make the Phase85 contract snapshot show `generate_chapter` as adapter-backed;
- keep model API mocking in tests, no real LLM calls.

Do not:

- change prompts;
- change frontend;
- change chapter quality policies;
- generate Chapter 27;
- add broad orchestration features beyond this adapter.

## Files

- Create: `backend/app/services/writing_agent/chapter_generation_tool.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify if needed: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase86-generate-chapter-agent-adapter.md`

## Task 1: RED Test For Adapter Metadata And Contract Gap Removal

- [ ] **Step 1: Add failing executor assertions**

In `backend/tests/test_writing_agent_tool_executor.py`, update existing adapter-name and metadata tests:

```python
assert "generate_chapter" in names

metadata = writing_agent_tool_adapter_metadata("generate_chapter")
assert metadata == {
    "tool_name": "generate_chapter",
    "adapter_type": "static",
    "category": "generation",
    "mutability": "write",
    "handler_name": "_generate_chapter",
}
```

In `test_tool_executor_handles_inspect_agent_tool_contracts`, assert:

```python
assert tools_by_name["generate_chapter"]["adapter_type"] == "static"
assert "missing_agent_native_adapter" not in tools_by_name["generate_chapter"]["gap_codes"]
```

- [ ] **Step 2: Run RED tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: fail because `generate_chapter` is not yet registered as a static adapter.

## Task 2: Implement Dedicated Generate-Chapter Tool Module

- [ ] **Step 1: Create module**

Create `backend/app/services/writing_agent/chapter_generation_tool.py` with:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import ChapterContent, Project
from app.services.actions.action_execution_service import ActionExecutionService

CONTINUITY_KEY_TERMS = ("空白信", "雾晶", "记忆雾晶", "钥匙", "下城", "黑市", "灯塔", "实验体", "叶知秋", "苏晚晴", "林深")


async def execute_generate_chapter_tool(
    db: Session,
    project_id: str,
    *,
    chapter_index: int,
    command_args: str | None = None,
    action_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    continuity = chapter_continuity_feedback(db, project_id, chapter_index)
    feedback = chapter_generation_feedback(db, project_id)
    result = await ActionExecutionService(db).execute(
        "generate_chapter",
        project_id,
        command_args=effective_chapter_command_args(command_args, continuity, feedback),
        action_params={**(action_params or {}), "chapter_index": chapter_index},
    )
    if continuity and isinstance(result, dict):
        result["agent_continuity_feedback"] = continuity
    if feedback and isinstance(result, dict):
        result["agent_generation_feedback"] = feedback
    return result
```

Move the existing private helper logic from `run_service.py` into this module, keeping behavior identical:

- `chapter_generation_feedback()`;
- `chapter_continuity_feedback()`;
- `previous_chapter_state_card()`;
- `effective_chapter_command_args()`.

If helper dependencies are currently private in `run_service.py`, either move the minimal dependencies with them or import stable public model/service functions. Do not introduce circular imports.

- [ ] **Step 2: Wire executor adapter**

In `backend/app/services/writing_agent/tool_executor.py`, add:

```python
async def _generate_chapter(context: WritingAgentToolContext, tool: WritingAgentToolRequest) -> dict[str, Any]:
    from app.services.writing_agent.chapter_generation_tool import execute_generate_chapter_tool

    chapter_index = _optional_int(tool.params.get("chapter_index")) or 1
    return await execute_generate_chapter_tool(
        context.db,
        context.project_id,
        chapter_index=chapter_index,
        command_args=tool.command_args,
        action_params=tool.params,
    )
```

Register:

```python
"generate_chapter": WritingAgentToolAdapter(
    "generate_chapter",
    _generate_chapter,
    category="generation",
    mutability="write",
),
```

- [ ] **Step 3: Remove run-service special-case execution**

In `WritingAgentRunService._execute_tool()`, remove the `if tool.tool_name == CHAPTER_TOOL_NAME:` branch and let `execute_writing_agent_tool()` handle `generate_chapter`.

Keep `_enrich_step_output()` unchanged so chapter length and world-model diagnostics still attach after the adapter output.

## Task 3: GREEN Tests And Focused Regression

- [ ] **Step 1: Run executor tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_static_adapter_names_are_report_or_agent_native_tools backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: pass.

- [ ] **Step 2: Run run-service regression around chapter generation**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "generate_chapter and (continuity or feedback or trace or generation)" -q
```

Expected: pass or no selected tests only if the expression does not match. If no tests are selected, run the specific existing tests that assert Writing Agent generation step behavior.

- [ ] **Step 3: Run related T1 slice**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "generate_chapter or inspect_agent_tool_contracts" -q
```

Expected: pass.

## Task 4: Report And T0 Checks

- [ ] **Step 1: Write Phase86 report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase86-generate-chapter-agent-adapter.md` with:

- summary;
- files changed;
- behavior preserved;
- validation commands and outputs;
- remaining gaps from `inspect_agent_tool_contracts`;
- next recommendation.

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
git status --short
git add backend/app/services/writing_agent/chapter_generation_tool.py backend/app/services/writing_agent/tool_executor.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-20-phase86-generate-chapter-agent-adapter.md docs/superpowers/notes/long-memory-agent/2026-05-20-phase86-generate-chapter-agent-adapter.md
git commit -m "feat: adapt chapter generation as agent tool"
git push origin main
```

Expected: main pushed.

