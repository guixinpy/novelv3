# Phase54 Context Diagnostics Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Writing Agent stop before generation when longform context diagnostics show stale/missing memory, then recommend and expose a repair tool.

**Architecture:** Keep `summarize_longform_context` read-only, but make its diagnostics actionable through `should_generate_next_chapter=false` and `recommended_actions=["repair_longform_maintenance"]`. Register `repair_longform_maintenance` as an internal write tool backed by existing Athena longform maintenance logic. Extend report stopping and recovery planning so a blocked auto-plan can preview the repair tool.

**Tech Stack:** FastAPI backend, SQLAlchemy, existing longform memory core service, Writing Agent tool registry/executor/run service/recovery planner, pytest.

---

## Reference Assimilation

Explorer results from the three reference projects were folded into the implementation:

- `openclaw`: diagnostics should be explicit, routeable, and recoverable through concrete next actions.
- `hermes-agent`: only hard context blockers should stop generation; informational context warnings should remain non-blocking.
- `openhuman`: recall and repair should be separated, with read-only diagnostics followed by explicit write tools.

novelv3 adaptation:

- `summarize_longform_context` stays read-only.
- The repair action is a separate Agent tool: `repair_longform_maintenance`.
- The run stops before `generate_chapter` when context is stale.
- Recovery preview can show the repair tool, but execution still goes through existing confirmation/hash guardrails.

## Files

- Modify: `backend/app/services/writing_agent/longform_context_summary.py`
  - Add `should_generate_next_chapter`, `recommended_actions`, and a decision object.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `repair_longform_maintenance`.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add static adapter for `repair_longform_maintenance`.
- Modify: `backend/app/services/writing_agent/run_service.py`
  - Let `summarize_longform_context` stop a run when it reports `should_generate_next_chapter=false`.
- Modify: `backend/app/services/writing_agent/recovery_policy.py`
  - Build a recovery recommendation from blocked context diagnostics.
- Modify: `backend/app/services/writing_agent/recovery_planner.py`
  - Allow recovery preview to find recommended recovery on a successful report step in a blocked run.
  - Add `repair_longform_maintenance` to safe recovery tools.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Add API tests for context gate blocking, recovery preview, repair tool, and ready auto-plan flow.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add registry assertions for the repair tool.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter metadata/dispatch assertions for the repair tool.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase54-context-diagnostics-recovery.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: RED for Actionable Context Diagnostics

- [x] **Step 1: Write failing API test**

Add a test where auto-plan continues to chapter 2 with no longform memory/retrieval maintenance. Expected:

- run status is `blocked`;
- steps are `describe_agent_tools`, `summarize_longform_context`;
- no `generate_chapter` action is called;
- context output has `should_generate_next_chapter is False`;
- `recommended_actions == ["repair_longform_maintenance"]`;
- recovery preview from the blocked run selects `repair_longform_maintenance`.

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale"
```

Expected: fail because context summaries do not stop generation and recovery policy does not recognize them.

## Task 2: GREEN for Context Gate and Recovery

- [x] **Step 1: Make context output actionable**

In `summarize_longform_context()`, when `maintenance.ready_for_writing` is false:

- add `should_generate_next_chapter=False`;
- add `recommended_actions=["repair_longform_maintenance"]`;
- include `decision.status="blocked"` and `decision.reason="longform_memory_needs_maintenance"`.

When healthy:

- `should_generate_next_chapter=True`;
- `recommended_actions=["preflight_writing"]`;
- `decision.status="ready"`.

- [x] **Step 2: Stop after context report**

In `_should_stop_after_report()`, add `summarize_longform_context` to the report tools that can stop follow-up generation.

- [x] **Step 3: Add recovery policy**

In `build_writing_agent_recovery()`, handle `summarize_longform_context` when output recommends `repair_longform_maintenance`.

- [x] **Step 4: Let recovery preview see successful report blockers**

Update `_latest_recommended_recovery()` so a blocked run can find a successful step whose `agent_tool_result.recovery.status == "recommended"`.

- [x] **Step 5: Run focused GREEN**

Run the focused test again. Expected: pass.

## Task 3: Repair Tool Contract

- [x] **Step 1: Write registry/executor/API tests**

Tests should assert:

- descriptor exists with `category="maintenance"`, `target_type="longform_maintenance"`, internal true;
- adapter metadata mutability is `write`;
- direct Agent run of `repair_longform_maintenance` returns `status="completed"`.

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "repair_longform_maintenance"
```

Expected: fail because the tool is not registered.

- [x] **Step 3: Register and adapt tool**

Add descriptor and static adapter that calls:

```python
repair_longform_maintenance(db, project_id, limit=..., repair_limit=...)
```

- [x] **Step 4: Run GREEN**

Run the same focused command. Expected: pass.

## Task 4: Preserve Ready Auto-Plan Flow

- [x] **Step 1: Update ready auto-plan test**

Seed healthy longform maintenance before auto-plan generation, so the context gate permits generation.

- [x] **Step 2: Run focused ready test**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_executes_high_level_next_chapter_goal"
```

Expected: pass.

## Task 5: Verification and Report

- [x] **Step 1: Run T1 Agent verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 2: Run static checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase54-context-diagnostics-recovery.md`.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: gate generation on longform context health"
git push origin main
```
