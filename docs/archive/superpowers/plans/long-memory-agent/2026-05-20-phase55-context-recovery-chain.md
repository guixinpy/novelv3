# Phase55 Context Recovery Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Phase54's single repair recommendation into a recoverable Agent tool chain that can repair longform maintenance, re-check context, preflight writing, and resume generation after explicit confirmation.

**Architecture:** Keep recovery planning read-only by default. For `summarize_longform_context` blockers, the recovery recommendation will carry continuation tools after `repair_longform_maintenance`; `plan_recovery_tools` will preview the whole chain and hash it; `execute_recovery` will only run it when the user confirms the exact hash. Each tool still executes through the normal run service, so any failed re-check stops before generation.

**Tech Stack:** FastAPI backend, SQLAlchemy models, Writing Agent recovery policy/planner/run service, pytest.

---

## Reference Assimilation

Explorer results from the three reference projects were folded into this phase:

- `openclaw`: recovery should produce an explicit continuation route, not ask the user to repeat the whole request.
- `hermes-agent`: after remediation, the system should re-run context/preflight checks before continuing.
- `openhuman`: multi-step recovery should remain bounded, auditable, and tied to a stable plan snapshot.

novelv3 adaptation:

- Preview remains read-only.
- Execution requires confirmation and matching `plan_hash`.
- The recovery chain is only added for context maintenance blockers.
- The chain re-checks context before any chapter generation.
- The hash covers the project, source run/step, reason, affected chapter, and full tool sequence.

## Files

- Modify: `backend/app/services/writing_agent/recovery_policy.py`
  - Add `continuation_tools` for longform context recovery, including the blocked chapter index.
- Modify: `backend/app/services/writing_agent/recovery_planner.py`
  - Convert recovery recommendations into one or more tool requests.
  - Hash and validate the full tool sequence.
  - Keep existing single-tool recovery behavior for outline/setup/preflight blockers.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert recovery preview exposes the context recovery chain.
  - Assert confirmed recovery executes repair -> summarize -> preflight -> generate.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase55-context-recovery-chain.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: RED for Recovery Chain Preview

- [x] **Step 1: Write failing API assertion**

In `test_agent_auto_plan_longform_context_blocks_stale_maintenance_before_generation`, after previewing recovery, assert:

```python
assert [tool["tool_name"] for tool in recovery["tools"]] == [
    "repair_longform_maintenance",
    "summarize_longform_context",
    "preflight_writing",
    "generate_chapter",
]
assert recovery["tools"][1]["params"]["chapter_index"] == 2
assert recovery["tools"][2]["params"]["chapter_index"] == 2
assert recovery["tools"][3]["params"]["chapter_index"] == 2
assert recovery["trace"]["selected_tools"] == [
    "repair_longform_maintenance",
    "summarize_longform_context",
    "preflight_writing",
    "generate_chapter",
]
assert recovery["execution_policy"]["safe_auto_execute"] is False
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale"
```

Expected: fail because preview currently returns only `repair_longform_maintenance`.

## Task 2: RED for Confirmed Recovery Execution

- [x] **Step 1: Add failing execution test**

Add a test that:

- creates a stale longform context blocked run for chapter 2;
- previews recovery to get `plan_hash`;
- confirms `execute_recovery`;
- monkeypatches `ActionExecutionService.execute` so `generate_chapter` succeeds without a real model call;
- expects the executed run steps to be:

```python
[
    "repair_longform_maintenance",
    "summarize_longform_context",
    "preflight_writing",
    "generate_chapter",
]
```

The test should also assert `summarize_longform_context` returns `should_generate_next_chapter is True` after repair.

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_recovery_chain"
```

Expected: fail because execution currently runs only the single repair tool.

## Task 3: GREEN for Chain Recommendation

- [x] **Step 1: Add continuation tools in recovery policy**

In `_longform_context_recovery()`, read `chapter_index` from the context summary output. If positive, include:

```python
"continuation_tools": [
    {
        "tool_name": "summarize_longform_context",
        "params": {
            "chapter_index": chapter_index,
            "query": f"恢复长篇维护后，重新汇总第{chapter_index}章写作上下文。",
        },
    },
    {"tool_name": "preflight_writing", "params": {"chapter_index": chapter_index}},
    {"tool_name": "generate_chapter", "params": {"chapter_index": chapter_index}},
]
```

Do not add continuation tools when the chapter index is missing.

- [x] **Step 2: Run focused RED**

Run the preview test again. Expected: still fail until recovery planner consumes the continuation tools.

## Task 4: GREEN for Planner Tool Sequence

- [x] **Step 1: Convert recovery to a full tool sequence**

In `recovery_planner.py`, replace the single `_tool_request_from_recovery()` path with a sequence builder:

- first tool: existing `next_tool`;
- later tools: valid dicts from `continuation_tools`;
- every tool gets a planner object with `planner_version`.

- [x] **Step 2: Hash and guard the full sequence**

Use the full tool sequence in:

- `hash_payload["tools"]`;
- `tools`;
- `trace["selected_tools"]`;
- `safe_auto_execute`.

Guardrail validation must check every selected tool is registered and visible now. Existing single-tool recoveries must keep the same output shape except that `tools` is a one-item list.

- [x] **Step 3: Run focused GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain or auto_plan_executes_recovery_after_hash_confirmation"
```

Expected: pass.

## Task 5: Verification and Report

- [x] **Step 1: Run T1 recovery and planner verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 2: Run static checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase55-context-recovery-chain.md`.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: resume generation after longform context repair"
git push origin main
```
