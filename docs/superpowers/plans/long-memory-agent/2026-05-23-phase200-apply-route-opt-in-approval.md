# Phase200 Apply Route Opt-In Approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the guarded mutation tool that applies the Phase198 pending action route opt-in diff only after a Phase199 approval contract is confirmed.

**Architecture:** Keep the mutation narrow: update only `PendingAction.params` with the recomputed `params_after`, do not execute the pending action, and do not mutate dialog state. The adapter must validate confirmation inputs, scope the pending action to the current project, recompute Phase198 preview plus Phase199 contract from current DB state, compare hash and snapshot, then assign a new JSON object to `pending.params` and commit.

**Tech Stack:** Python, pytest, SQLAlchemy JSON column assignment, existing Writing Agent descriptor/adapter registry.

---

## Scope

- New internal tool: `apply_pending_action_route_approval_opt_in`.
- Mutability: adapter `write`; descriptor has `confirm_apply`, `approval_contract_hash`, `approval_contract`, so tool contract projection classifies it as `guarded_write`.
- No pending action execution and no dialog state transition.
- No write unless all confirmation checks pass.
- Missing/foreign pending action must return generic `pending_action_not_found` and must not expose foreign params.

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
  - Add `PENDING_ACTION_ROUTE_OPT_IN_APPLY_VERSION`.
  - Add output helpers for apply success/blocked result.
  - Add verification helper comparing caller hash/snapshot to recomputed Phase199 contract.
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - Add adapter map entry.
  - Add handler that validates confirmation fields, scopes pending action, recomputes preview/contract, and assigns `pending.params = params_after`.
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - Add descriptor after Phase199 contract descriptor.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Add happy path, confirmation block, mismatch block, stale block, foreign ownership, no-op guard, metadata, static adapter, unhandled internal, and tool contract tests.
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
  - Add descriptor order and descriptor schema assertions.
- Modify: `backend/tests/test_writing_agent_write_gate_coverage.py`
  - Add direct confirmation guard projection assertion for the new tool.
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase200-apply-route-opt-in-approval.md`

## Acceptance Criteria

- Happy path:
  - Caller first obtains Phase199 contract.
  - Apply with `confirm_apply=True`, matching `approval_contract_hash`, and matching `approval_contract`.
  - Output `status == "success"` and `write_performed is True`.
  - `PendingAction.params.agent_route.use_agent_approval_chain is True` after refresh/requery.
- Guard failures:
  - Missing `confirm_apply` blocks before write.
  - Missing hash or missing contract blocks before write.
  - Hash mismatch blocks before write.
  - Snapshot mismatch blocks before write.
  - Stale pending params/status blocks before write.
  - Already-declared/no-diff route returns blocked/not_required and does not write.
  - Foreign project pending action returns `pending_action_not_found` without params leakage.
- Registry:
  - New descriptor is internal, not non-blocking report, required fields include `pending_action_id`, `confirm_apply`, `approval_contract_hash`, `approval_contract`.
  - Adapter metadata exists with `mutability == "write"`.
  - Tool contract projection reports `mutability == "guarded_write"` and `requires_confirmation is True`.

## Tasks

### Task 1: RED Tests

- [x] Add failing happy-path apply test in `backend/tests/test_writing_agent_tool_executor.py`.
- [x] Add failing block tests:
  - missing confirmation
  - hash mismatch
  - contract snapshot mismatch
  - stale params/status
  - foreign project leakage
  - already declared/no diff
- [x] Add failing metadata/static/unhandled/tool-contract tests.
- [x] Add failing descriptor test in `backend/tests/test_writing_agent_tool_registry.py`.
- [x] Add failing write gate coverage test in `backend/tests/test_writing_agent_write_gate_coverage.py`.
- [x] Run RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
pytest backend/tests/test_writing_agent_write_gate_coverage.py -k "apply_route_opt_in" -q
```

Expected: failures because descriptor/adapter/apply helper do not exist.

### Task 2: GREEN Implementation

- [x] Add apply version and helper outputs in `slash_command_route.py`.
- [x] Add adapter entry and handler in `agent_core_tool_adapters.py`.
- [ ] Handler order:
  - Validate `confirm_apply`.
  - Validate `approval_contract_hash` and `approval_contract`.
  - Query pending action and scope by dialog/project.
  - Validate `pending.status == "pending"` and `resolved_at is None`.
  - Recompute Phase198 preview and Phase199 contract.
  - Require recomputed contract `status == "requires_confirmation"`.
  - Compare caller hash, caller embedded hash, and caller contract snapshot to recomputed contract.
  - Assign deep-copied `params_after` to `pending.params`, commit, refresh.
- [x] Add descriptor in `agent_core_tool_descriptors.py`.
- [x] Run T1 selected tests:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "apply_route_opt_in_approval or route_opt_in_apply" -q
pytest backend/tests/test_writing_agent_write_gate_coverage.py -k "apply_route_opt_in" -q
```

Expected: selected tests pass.

### Task 3: Targeted Regression

- [x] Run T2 route/write-gate slice:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_route_opt_in_approval or route_opt_in_apply_contract or route_opt_in_apply or pending_action_route_opt_in_plan or route_approval_opt_in_plan or static_adapter_names or unhandled_internal or inspect_agent_tool_contracts or agent_core_tool_adapters" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "apply_route_opt_in_approval or route_opt_in_apply_contract or route_opt_in_apply_preview or route_approval_opt_in_plan or agent_core_tool_descriptors" -q
pytest backend/tests/test_writing_agent_write_gate_coverage.py -q
python -m compileall backend/app/services/writing_agent
```

Expected: selected tests pass and compile exits 0.

### Task 4: Review, Hygiene, Commit

- [x] Request code review focused on confirmation bypass and params leakage.
- [x] Fix Critical/Important findings with tests.
- [x] Write phase report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase200-apply-route-opt-in-approval.md
```

- [x] Run hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Expected: diff check exits 0; secret scan exits 1 with no matches.

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_write_gate_coverage.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase200-apply-route-opt-in-approval.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase200-apply-route-opt-in-approval.md
git commit -m "feat: apply route opt in approval"
git push origin main
```

## Subagent Notes

Explorer `019e5474-f86f-7e32-a189-5aeb6dacc8b1` recommended:

- Use existing approved execution pattern: preview/prepare are read; apply/execute is write with confirmation fields.
- Assign a new JSON object to `PendingAction.params`, not nested in-place mutation.
- Recompute preview and contract from current DB state before trusting caller hash/snapshot.
- Foreign/missing pending action must not leak params.
