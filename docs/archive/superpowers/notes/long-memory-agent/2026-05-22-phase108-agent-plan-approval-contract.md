# Phase108 Agent Plan Approval Contract Report

## Phase Summary

Phase108 added a read-only approval contract preview for Writing Agent plans. Plans now expose a deterministic `approval_contract` that lists write or guarded-write steps and binds them to a stable `approval_contract_hash`.

## Goal Alignment

- Moves novelv3 toward an Agent core that can plan, request approval, and later execute tool chains without relying on user-written long prompts.
- Keeps Hermes, Athena/world-model, review, queue, and other modules as Agent-callable tools with clearer safety boundaries.
- Separates planning/preview from execution: this phase does not change runtime execution behavior and does not add an approval gate yet.
- Uses the Phase107 `plan_id`, `step_id`, `mutability`, and `requires_confirmation` metadata as the base for approval readiness.

## Implemented

- Added `backend/app/services/writing_agent/approval_contract.py`.
- Added `build_agent_plan_approval_contract()`:
  - returns `requires_confirmation` when a plan contains `write` or `guarded_write` steps.
  - returns `not_required` for read-only plans.
  - returns `invalid_plan` for invalid input.
  - creates a deterministic `approval:<sha>` hash from stable JSON.
- Bound the hash payload to:
  - contract version.
  - project id.
  - plan id.
  - source projection id.
  - planner version.
  - intent class.
  - write-step index/id/tool/params/mutability/reason.
- Added `approval_contract` to base planner output.
- Added top-level `approval_contract` to dialog-intent-originated plans.
- Registered `preview_agent_plan_approval_contract` as an internal non-blocking preflight tool.
- Added static executor adapter for `preview_agent_plan_approval_contract`.

## Subagent / Reference Review

Read-only subagent review recommended:

- Do not rely on `step_id` alone for approval.
- Bind approval hashes to the semantics users approve, including plan metadata and write-step params.
- Keep preview strictly read-only.
- Avoid global signing systems or a generic workflow DSL in this phase.
- Later execution should re-read live state and recompute hashes before allowing writes.

The implementation follows the read-only and stable-hash parts now. Live-state drift checks are intentionally deferred to the future approval enforcement phase.

## Novel Progress

No novel chapter was generated in this phase. This phase strengthens the Agent control plane so future autonomous long-running generation can safely move from plan to approval to execution.

## Verification

Red test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "approval_contract or ready_next_chapter or review_only or dialog_intent_agent_plan_for_chapter or handles_planner_tool or static_adapter_names or unhandled_internal" -q
```

Initial result:

```text
ERROR backend/tests/test_writing_agent_approval_contract.py
ModuleNotFoundError: No module named 'app.services.writing_agent.approval_contract'
```

Focused green result:

```text
12 passed, 99 deselected
```

T1 module coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_planner.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

```text
111 passed
```

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

```text
No whitespace errors. No active secret matches.
```

## Next Phase Recommendation

Phase109 should decide how approval contracts are consumed. Recommended next step: add a read-only execution preflight that recomputes the approval contract from the current plan/live state and reports drift before any actual write tool can consume `approval_contract_hash`.
