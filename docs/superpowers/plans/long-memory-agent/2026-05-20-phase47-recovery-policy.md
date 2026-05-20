# Phase47 Recovery Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic recovery advice to `agent_tool_result` for blocked/failed Writing Agent steps, starting with `preflight_writing` blocker cases.

**Architecture:** Keep recovery as read-only structured advice inside the normalized result envelope. Do not auto-run recovery tools in this phase. A small recovery policy module maps step output and planner metadata to suggested next tools and stop/continue guidance.

---

## Why This Phase

Phases 43-46 made tool execution observable. The next Agent capability is using that structured output to recover from predictable blocks.

The immediate target is `preflight_writing` because it already emits structured blocker issues:

- missing setup;
- missing target outline chapter;
- missing historical outline chapters;
- missing previous chapter;
- repeated chapter length drift.

The Agent should not need to parse Chinese error strings to decide next steps.

## Scope

In scope:

- Add a recovery policy helper for Writing Agent tool results.
- Attach `recovery` to `agent_tool_result`.
- Cover `preflight_writing` blocked cases:
  - `missing_setup`;
  - `missing_outline_chapter`;
  - `missing_historical_outline_chapters`;
  - `missing_previous_chapter`;
  - fallback unknown blocker.
- Preserve existing run statuses and tool execution order.

Out of scope:

- Automatically executing recovery tools.
- Retry loops.
- UI changes.
- Recovery policies for all tools.
- Long-running task queue integration.

## Proposed Recovery Shape

```python
"recovery": {
    "status": "recommended",
    "source_tool": "preflight_writing",
    "reason_code": "missing_outline_chapter",
    "action": "run_tool",
    "next_tool": "expand_outline_window",
    "next_params": {"start_chapter": 3, "end_chapter": 3},
    "should_continue_current_run": False,
    "requires_user_input": False,
    "message": "第3章缺少章节大纲，建议先补齐目标章节大纲。"
}
```

If no policy applies:

```python
"recovery": {
    "status": "none",
    "source_tool": "preflight_writing"
}
```

## Task 1: Write Failing Tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] **Step 1: Missing outline recovery**

Extend `test_agent_preflight_blocks_when_target_outline_is_missing` to assert recovery recommends:

- `next_tool == "expand_outline_window"`;
- `next_params == {"start_chapter": 3, "end_chapter": 3}`;
- `should_continue_current_run is False`.

- [x] **Step 2: Historical outline gap recovery**

Extend `test_agent_preflight_blocks_when_generated_chapter_outline_gap_exists` to assert recovery recommends:

- `next_tool == "backfill_outline_gaps"`;
- `next_params == {"before_chapter": 4}`.

- [x] **Step 3: Missing previous chapter recovery**

Add a test for `preflight_writing` chapter 3 with outline 1-3 and generated chapter 1. Assert recovery recommends generating chapter 2 before continuing chapter 3.

- [x] **Step 4: Verify red**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "preflight_blocks_when_target_outline_is_missing or preflight_blocks_when_generated_chapter_outline_gap_exists or missing_previous_chapter_recovery"
```

Expected: FAIL because recovery is not present yet.

## Task 2: Implement Recovery Policy

**Files:**

- Add: `backend/app/services/writing_agent/recovery_policy.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] **Step 1: Add helper**

Create `build_writing_agent_recovery(tool_name, step_status, output, planner)` returning a dict.

- [x] **Step 2: Implement preflight policies**

Map blocker issue codes to deterministic next tools.

- [x] **Step 3: Attach to envelope**

Add `recovery` to `_agent_tool_result_envelope()`.

## Task 3: Verify and Report

**Files:**

- Modify: this plan checklist.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase47-recovery-policy.md`

- [x] **Step 1: Run focused GREEN**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "preflight_blocks_when_target_outline_is_missing or preflight_blocks_when_generated_chapter_outline_gap_exists or missing_previous_chapter_recovery"
```

- [x] **Step 2: Run T1 module verification**

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 3: Static checks**

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 4: Write report, commit, push**
