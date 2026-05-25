# Phase87 Generate Chapter Output Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten `generate_chapter` into a structured Agent output contract after the Phase86 adapter migration.

**Architecture:** Keep the existing generation behavior and model calls unchanged. Add contract metadata around the adapter result and update the registry output schema so planner and Trace consumers can reliably read chapter id, trace id, contextual feedback, Athena analysis, and recommended post-generation tools.

**Tech Stack:** Python, Writing Agent service layer, pytest.

---

## Scope

Do:

- add structured output schema for `generate_chapter`;
- add `recommended_next_tools` to successful adapter output;
- keep existing result fields and status semantics;
- make `inspect_agent_tool_contracts` stop flagging `generate_chapter` as `output_schema_too_generic`;
- add focused tests.

Do not:

- change prompts;
- change API response shape beyond additive fields;
- run real model generation;
- rewrite planner ordering in this phase.

## Files

- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/chapter_generation_tool.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase87-generate-chapter-output-contract.md`

## Task 1: RED Tests For Structured Contract

- [ ] **Step 1: Add registry test**

In `backend/tests/test_writing_agent_tool_registry.py`, add:

```python
def test_agent_tool_registry_generate_chapter_has_structured_output_contract():
    descriptor = get_agent_tool_descriptor("generate_chapter")

    assert descriptor is not None
    properties = descriptor.output_schema["properties"]
    assert {"status", "chapter_index", "trace_id", "athena_analysis", "agent_continuity_feedback", "agent_generation_feedback", "recommended_next_tools"}.issubset(properties)
    assert properties["chapter_index"]["type"] == "integer"
    assert properties["recommended_next_tools"]["type"] == "array"
```

- [ ] **Step 2: Add adapter output test**

In `backend/tests/test_writing_agent_tool_executor.py`, update `test_generate_chapter_tool_appends_context_without_run_service`:

```python
assert result["recommended_next_tools"] == [
    "review_chapter_quality",
    "review_chapter_continuity",
    "analyze_chapter_world_model",
]
```

Update `test_tool_executor_handles_inspect_agent_tool_contracts`:

```python
assert "output_schema_too_generic" not in tools_by_name["generate_chapter"]["gap_codes"]
```

- [ ] **Step 3: Run RED tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_generate_chapter_has_structured_output_contract backend/tests/test_writing_agent_tool_executor.py::test_generate_chapter_tool_appends_context_without_run_service backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: fail because output schema and recommended tools are not yet present.

## Task 2: Implement Structured Output Contract

- [ ] **Step 1: Add schema in registry**

In `backend/app/services/writing_agent/tool_registry.py`, replace `generate_chapter` output schema with:

```python
output_schema=_object_schema(
    {
        "status": {"type": "string"},
        "chapter_index": {"type": "integer"},
        "trace_id": {"type": "string"},
        "athena_analysis": {"type": "object"},
        "agent_continuity_feedback": {"type": "object"},
        "agent_generation_feedback": {"type": "object"},
        "chapter_length_decision": {"type": "object"},
        "world_model_proposal_diagnostic": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
    }
)
```

- [ ] **Step 2: Add post-generation next tools**

In `backend/app/services/writing_agent/chapter_generation_tool.py`, define:

```python
POST_GENERATION_NEXT_TOOLS = [
    "review_chapter_quality",
    "review_chapter_continuity",
    "analyze_chapter_world_model",
]
```

After successful `ActionExecutionService` result, add:

```python
if isinstance(result, dict) and str(result.get("status") or "") == "success":
    result.setdefault("recommended_next_tools", list(POST_GENERATION_NEXT_TOOLS))
```

Do not overwrite explicit downstream values if a future generator already provides `recommended_next_tools`.

## Task 3: Validation And Report

- [ ] **Step 1: Run focused tests**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_generate_chapter_has_structured_output_contract backend/tests/test_writing_agent_tool_executor.py::test_generate_chapter_tool_appends_context_without_run_service backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: pass.

- [ ] **Step 2: Run related T1 slice**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

Expected: pass.

- [ ] **Step 3: Write report and T0 checks**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase87-generate-chapter-output-contract.md`.

Run:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Expected:

- `git diff --check` exits `0`;
- `rg` exits `1` with no output.

## Task 4: Commit And Push

- [ ] **Step 1: Commit**

Run:

```powershell
git status --short
git add backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/chapter_generation_tool.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-20-phase87-generate-chapter-output-contract.md docs/superpowers/notes/long-memory-agent/2026-05-20-phase87-generate-chapter-output-contract.md
git commit -m "feat: structure chapter generation agent output"
```

- [ ] **Step 2: Push**

Run:

```powershell
git push origin main
```

