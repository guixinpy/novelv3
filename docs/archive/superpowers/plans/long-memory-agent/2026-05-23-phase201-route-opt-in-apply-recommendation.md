# Phase201 Route Opt-In Apply Recommendation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the Phase199/200 pending-action route opt-in contract/apply chain into the Agent recommendation flow without exposing approval hashes in ordinary UI.

**Architecture:** Keep `apply_pending_action_route_approval_opt_in` guarded and non-auto-executable. Treat `preview_pending_action_route_approval_opt_in_apply_contract` as the safe recommended follow-up that can prepare the approval contract, then let the contract preview recommend the guarded apply tool for Agent-internal confirmation.

**Tech Stack:** Python backend, SQLAlchemy models, pytest, TypeScript/Vitest chat projection.

---

### Task 1: Backend Recommendation Contract

**Files:**
- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Write failing assertions**

Add assertions to `test_tool_executor_previews_pending_route_opt_in_apply_contract`:

```python
assert result.output["recommended_next_tools"] == ["apply_pending_action_route_approval_opt_in"]
assert result.output["recommended_next_tool_calls"] == [
    {
        "tool_name": "apply_pending_action_route_approval_opt_in",
        "visibility": "agent_internal",
        "requires_confirmation": True,
        "params": {
            "pending_action_id": pending.id,
            "confirm_apply": True,
            "approval_contract_hash": result.output["approval_contract_hash"],
            "approval_contract": result.output["approval_contract"],
        },
    }
]
```

Add assertions to the blocked/not-required contract tests:

```python
assert result.output["recommended_next_tools"] == []
assert result.output["recommended_next_tool_calls"] == []
```

- [ ] **Step 2: Run RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract" -q
```

Expected: fails because the contract output does not yet include `recommended_next_tools` / `recommended_next_tool_calls`.

- [ ] **Step 3: Implement minimal contract output**

In `_route_opt_in_contract_output`, return:

```python
recommended_next_tools = ["apply_pending_action_route_approval_opt_in"] if status == "requires_confirmation" else []
recommended_next_tool_calls = []
if status == "requires_confirmation" and approval_contract_hash and approval_contract:
    recommended_next_tool_calls.append(
        {
            "tool_name": "apply_pending_action_route_approval_opt_in",
            "visibility": "agent_internal",
            "requires_confirmation": True,
            "params": {
                "pending_action_id": str(route_apply_preview.get("pending_action_id") or ""),
                "confirm_apply": True,
                "approval_contract_hash": approval_contract_hash,
                "approval_contract": approval_contract,
            },
        }
    )
```

Add both fields to the descriptor output schema for `preview_pending_action_route_approval_opt_in_apply_contract`.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_contract" -q
```

Expected: all selected tests pass.

### Task 2: Recommended Follow-Up Planner

**Files:**
- Modify: `backend/app/services/writing_agent/recommended_followup_planner.py`
- Test: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] **Step 1: Write failing tests**

Add a test where a previous successful step recommends `preview_pending_action_route_approval_opt_in_apply_contract` and has `pending_action_id` in its output. Expected planned tool:

```python
assert result.output["tools"] == [
    {
        "tool_name": "preview_pending_action_route_approval_opt_in_apply_contract",
        "params": {"pending_action_id": pending.id},
        ...
    }
]
```

Add a test where a previous contract-preview step recommends `apply_pending_action_route_approval_opt_in`. Expected:

```python
assert result.output["tools"] == []
assert result.output["trace"]["rejected_tools"] == [
    {"tool_name": "apply_pending_action_route_approval_opt_in", "reason": "requires_confirmation"}
]
```

- [ ] **Step 2: Run RED**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or route_opt_in" -q
```

Expected: the preview-contract follow-up is rejected or lacks `pending_action_id`.

- [ ] **Step 3: Implement minimal planner support**

In `recommended_followup_planner.py`:

- Add `preview_pending_action_route_approval_opt_in_apply_contract` to `SAFE_RECOMMENDED_FOLLOWUP_TOOLS`.
- Do not add `apply_pending_action_route_approval_opt_in` to the safe list.
- Add `_source_pending_action_id(step)` that reads, in order, top-level step output, `agent_tool_result.output`, and input params.
- In `_params_for_followup`, when the descriptor has `pending_action_id`, populate it from `_source_pending_action_id`.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or route_opt_in" -q
```

Expected: selected tests pass.

### Task 3: Frontend Safe Projection

**Files:**
- Modify: `frontend/src/components/chat/agentRunProjection.ts`
- Test: `frontend/src/components/chat/agentRunProjection.test.ts`

- [ ] **Step 1: Write failing tests**

Add tests for:

```ts
buildAgentRunActionResultView({
  type: 'preview_pending_action_route_approval_opt_in_apply_contract',
  status: 'success',
  data: {
    status: 'requires_confirmation',
    approval_contract_hash: 'approval:secret',
    recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
  },
})
```

Expected label `路由升级契约待确认`; `JSON.stringify(view)` must not contain `approval:secret`.

Add an apply success/blocked fallback view test; it should show status/reason/write summary and never hash.

- [ ] **Step 2: Run RED**

Run:

```powershell
npm --prefix frontend run test -- agentRunProjection
```

Expected: unsupported action type returns `null`.

- [ ] **Step 3: Implement minimal projection descriptors**

Add both action types to `AGENT_RUN_ACTION_TYPES` and descriptor map:

- `preview_pending_action_route_approval_opt_in_apply_contract`
- `apply_pending_action_route_approval_opt_in`

Build detail items from safe fields only: internal status, reason, write performed, next-tool count. Do not include contract hash, full contract, route diff, or params.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
npm --prefix frontend run test -- agentRunProjection
```

Expected: selected frontend tests pass.

### Task 4: Verification, Report, Commit

**Files:**
- Modify: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase201-route-opt-in-apply-recommendation.md`

- [ ] **Step 1: Run T1/T2 validation**

Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "recommended_followups or route_opt_in_apply_contract or apply_route_opt_in" -q
npm --prefix frontend run test -- agentRunProjection
python -m compileall backend/app/services/writing_agent
git diff --check
rg -n "sk-[A-Za-z0-9]{8,}" .
```

Expected: tests pass; compile and diff check exit 0; secret scan has no real key match.

- [ ] **Step 2: Request code review**

Ask a review subagent to inspect the diff for:

- accidental auto-execution of guarded apply;
- approval hash leakage in user-facing projection;
- missing pending-action scoping.

- [ ] **Step 3: Update report and commit**

Update the Phase201 report with red/green evidence, review result, files changed, and next phase.

Commit:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/app/services/writing_agent/recommended_followup_planner.py backend/tests/test_writing_agent_tool_executor.py frontend/src/components/chat/agentRunProjection.ts frontend/src/components/chat/agentRunProjection.test.ts docs/superpowers/plans/long-memory-agent/2026-05-23-phase201-route-opt-in-apply-recommendation.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase201-route-opt-in-apply-recommendation.md
git commit -m "feat: route opt in apply recommendations"
git push
```
