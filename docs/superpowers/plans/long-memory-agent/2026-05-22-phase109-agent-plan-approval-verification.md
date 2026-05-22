# Phase109 Agent Plan Approval Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only approval verification preflight for Writing Agent plans so later execution phases can detect missing, mismatched, or stale approval contract hashes before write tools run.

**Architecture:** Phase108 creates a deterministic approval contract from plan write steps. Phase109 adds a verification layer that recomputes the contract from the current plan, compares the supplied approval hash and optional approved contract snapshot, and returns a structured drift report. This remains read-only and does not enforce execution or change any write-tool behavior.

**Tech Stack:** FastAPI backend service layer, existing Writing Agent tool registry/executor, pytest.

---

## Phase Scope

- Phase number: 109.
- Goal alignment: strengthens Agent tool orchestration by separating plan preview, approval hash verification, and future execution enforcement.
- Novel progress: no new chapter generation; this is Agent control-plane safety infrastructure.
- Verification level: T1. Scope is local to Writing Agent approval planning and static adapters.
- Not doing:
  - No actual execution gate.
  - No database schema changes.
  - No frontend work.
  - No full live-state binding for chapter/revision/world-model state.
  - No model/API calls.

## Files

- Modify: `backend/app/services/writing_agent/approval_contract.py`
  - Add `verify_agent_plan_approval_contract()`.
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - Register `verify_agent_plan_approval_contract`.
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - Add static adapter for the verify tool.
- Modify: `backend/tests/test_writing_agent_approval_contract.py`
  - Add verification behavior tests.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor assertions.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add adapter dispatch and migration tracking assertions.
- Create final report: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase109-agent-plan-approval-verification.md`

## Task 1: Approval Verification Function

**Files:**
- Modify: `backend/app/services/writing_agent/approval_contract.py`
- Test: `backend/tests/test_writing_agent_approval_contract.py`

- [ ] **Step 1: Write failing tests**

Add tests:

```python
def test_verify_approval_contract_accepts_matching_hash():
    plan = _write_plan(project_id="project-1")
    contract = build_agent_plan_approval_contract(plan)

    result = verify_agent_plan_approval_contract(
        plan,
        approval_contract_hash=contract["approval"]["approval_contract_hash"],
        approval_contract=contract,
        project_id="project-1",
    )

    assert result["status"] == "ready"
    assert result["reason"] == "approval_contract_verified"
    assert result["drift"]["hash_matches"] is True
    assert result["drift"]["project_matches"] is True


def test_verify_approval_contract_blocks_hash_mismatch():
    plan = _write_plan(project_id="project-1")

    result = verify_agent_plan_approval_contract(plan, approval_contract_hash="approval:bad", project_id="project-1")

    assert result["status"] == "blocked"
    assert result["reason"] == "approval_contract_hash_mismatch"
    assert result["drift"]["hash_matches"] is False
    assert result["recommended_next_tools"] == ["preview_agent_plan_approval_contract"]
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -k verify_approval_contract -q
```

Expected: fail because `verify_agent_plan_approval_contract` is missing.

- [ ] **Step 3: Implement minimal verifier**

Implementation requirements:

- Recompute current contract via `build_agent_plan_approval_contract(plan)`.
- If current contract is `invalid_plan`, return `status="invalid_plan"`.
- If current contract does not require approval, return `status="not_required"`.
- If expected hash is missing, return `status="blocked"` and `reason="approval_contract_hash_required"`.
- If expected hash differs from current hash, return `status="blocked"` and `reason="approval_contract_hash_mismatch"`.
- If optional approved contract snapshot has a different hash, return `status="blocked"` and `reason="approval_contract_snapshot_mismatch"`.
- If optional `project_id` differs from plan contract project id, return `status="blocked"` and `reason="approval_contract_project_mismatch"`.
- If all checks pass, return `status="ready"` and `reason="approval_contract_verified"`.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -q
```

Expected: pass.

## Task 2: Registry and Executor Tool

**Files:**
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Test: `backend/tests/test_writing_agent_tool_registry.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert:

- `verify_agent_plan_approval_contract` exists.
- It is internal, non-blocking, preflight, read-only by contract, and targets `agent_plan_approval_verification`.
- Static adapter names include it.
- Unhandled internal tool tracking excludes it.
- Executing it with a matching hash returns `ready`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "approval_contract or static_adapter_names or unhandled_internal" -q
```

Expected: fail because the descriptor and adapter are missing.

- [ ] **Step 3: Implement descriptor and adapter**

Add descriptor near Phase108 preview tool. Add executor handler that passes `plan`, `approval_contract_hash`, optional `approval_contract`, and current `context.project_id` into the verifier.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "approval_contract or static_adapter_names or unhandled_internal" -q
```

Expected: pass.

## Task 3: T1 Verification, Report, Commit

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase109-agent-plan-approval-verification.md`

- [ ] **Step 1: Run T1 test scope**

Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -q
```

Expected: pass.

- [ ] **Step 2: Hygiene**

Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: no whitespace errors and no active secret matches.

- [ ] **Step 3: Write report**

Report must include:

- Actual changes.
- Why no novel chapter was generated.
- Subagent/reference review summary.
- Verification commands and results.
- Next phase recommendation.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git add backend/app/services/writing_agent/approval_contract.py backend/app/services/writing_agent/tool_registry.py backend/app/services/writing_agent/tool_executor.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-22-phase109-agent-plan-approval-verification.md docs/superpowers/notes/long-memory-agent/2026-05-22-phase109-agent-plan-approval-verification.md
git commit -m "feat: verify agent plan approval contracts"
git push
```

Expected: `main` remains aligned with `origin/main`.
