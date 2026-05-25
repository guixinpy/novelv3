# Phase109 Agent Plan Approval Verification Report

## Phase Summary

Phase109 added a read-only approval verification preflight for Writing Agent plans. It recomputes the current approval contract from a plan, compares the supplied approval hash and optional approved contract snapshot, and returns a structured drift report before any future write execution gate consumes the hash.

## Goal Alignment

- Moves novelv3 closer to a real Writing Agent control plane: plan -> approval preview -> approval verification -> future execution gate.
- Keeps module tools Agent-callable with clearer safety boundaries.
- Supports autonomous orchestration without relying on users to manually inspect every write step.
- Preserves the goal constraint that this phase is still read-only and does not alter write-tool execution semantics.

## Implemented

- Added `verify_agent_plan_approval_contract()` in `backend/app/services/writing_agent/approval_contract.py`.
- Verification now reports:
  - `ready` when supplied hash, optional snapshot, and project binding match.
  - `not_required` for read-only plans.
  - `blocked` for missing hash, hash mismatch, snapshot mismatch, or project mismatch.
  - `invalid_plan` for invalid input shape.
- Added drift fields:
  - `hash_matches`
  - `snapshot_hash_matches`
  - `project_matches`
  - expected / actual / snapshot approval hashes
  - write step count
- Registered `verify_agent_plan_approval_contract` as an internal, non-blocking preflight tool.
- Added static executor adapter for the verify tool.
- Added tests for verifier behavior, registry exposure, executor dispatch, and migration tracking.

## Subagent / Reference Review

Read-only subagent review recommended:

- Verify/preflight should check contract shape and hash, not execute tools.
- Tool contract consistency checks are useful but should remain read-only.
- Low-cost live-state drift is appropriate now; high-risk execution-time drift should stay in the actual execution gate.
- Avoid making Phase109 responsible for proving all future execution safety.

This phase implements the low-cost contract/hash/project checks. Tool-contract drift checks are left as the next incremental extension.

## Novel Progress

No novel chapter was generated in this phase. The phase improves the approval control plane needed before long-running autonomous generation can safely execute write chains.

## Verification

Red test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -k "verify_approval_contract or approval_contract_verification or static_adapter_names or unhandled_internal" -q
```

Initial result:

```text
ImportError: cannot import name 'verify_agent_plan_approval_contract'
```

Focused green result:

```text
8 passed, 104 deselected
```

T1 module coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

```text
112 passed
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

Phase110 should extend approval verification with read-only tool-contract drift checks for each write step: tool exists, adapter exists, current mutability still requires confirmation, and required input schema fields are present in step params.
