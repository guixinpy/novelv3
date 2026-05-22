# Phase111 Execution Approval Verification Gate Report

## Phase Summary

Phase111 connected Phase108-110 Agent plan approval verification to the existing longform batch execution path. The system now persists a minimal Agent plan approval contract during batch execution prepare, then fresh-verifies that contract before `execute_longform_chapter_batch` can invoke `generate_chapter`.

## Goal Alignment

- Moves novelv3 from read-only approval preflight toward an executable Agent control plane.
- Keeps the existing Phase61 attempt manifest and execution approval hash gate intact.
- Adds a second Agent-native verification layer for the actual write step that mutates manuscript content.
- Supports future autonomous longform generation by proving that execution can require both user-facing approval and live tool-contract verification.

## Implemented

- `prepare_longform_chapter_batch_execution` now builds and persists:
  - `agent_plan`
  - `agent_plan_approval_contract`
  - `agent_plan_approval_contract_hash`
- The persisted Agent plan models only the currently executed write step:
  - `tool_name == "generate_chapter"`
  - `params == {"chapter_index": selected_chapter}`
  - `mutability == "write"`
  - `requires_confirmation is True`
- The existing Phase61 approval contract now binds `agent_plan_approval_contract_hash`.
- `execute_longform_chapter_batch` now fresh-verifies persisted Agent approval before generation.
- `tool_executor.py` injects runtime tool metadata via `_approval_tool_metadata_by_name`, keeping `batch_execution.py` from depending on executor internals.
- Successful execution output now includes:
  - `evidence.agent_plan_approval_verified`
  - `agent_plan_approval_verification`
- Blocked execution now reports missing or drifted Agent approval evidence before any chapter write.

## Boundary Decision

Phase111 does not replace the existing longform batch approval contract. It layers Agent-native approval verification on top of the existing `attempt_manifest_hash + approval_contract_hash + confirm_execute` gate.

Dependency direction remains:

```text
tool_executor adapter
  -> batch_execution service
      -> approval_contract pure verifier
```

`approval_contract.py` remains read-only and pure. `batch_execution.py` consumes a narrow metadata provider and does not import `tool_executor.py`.

## Subagent Review

A read-only architecture subagent recommended:

- Keep Phase61 execution contract in place.
- Persist `agent_plan` and `agent_plan_approval_contract` during prepare.
- Fresh-verify the persisted plan before `generate_chapter`.
- Keep the plan narrow and only approve the write step actually executed in this phase.
- Block rather than allow execution when runtime tool metadata is unavailable.
- Avoid turning verifier into an executor or adding JSON Schema/DB availability validation.

The implementation follows these constraints.

## Novel Progress

No new novel chapter was generated in this phase. This phase improves the execution safety path that future autonomous long-running generation will use.

## Verification

RED prepare test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "prepare_longform_chapter_batch_execution_manifest" -q
```

Initial result:

```text
1 failed, 169 deselected
KeyError: 'agent_plan'
```

RED execute tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "execute_longform_chapter_batch" -q
```

Initial result:

```text
5 failed, 165 deselected
KeyError: 'agent_plan'
```

Focused green results:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "prepare_longform_chapter_batch_execution_manifest" -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "execute_longform_chapter_batch" -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "dispatches_execute_longform_chapter_batch_adapter" -q
```

Result:

```text
1 passed, 169 deselected
5 passed, 165 deselected
1 passed, 73 deselected
```

T1 related coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "longform_chapter_batch_execution or execute_longform_chapter_batch" -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

```text
8 passed, 162 deselected
116 passed
```

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

```text
git diff --check: no whitespace errors; PowerShell printed a CRLF normalization warning for backend/tests/test_writing_agent_runs.py
secret scan: no matches
```

## Next Phase Recommendation

Phase112 should reduce duplication between plan approval metadata projection and execution gates. A practical target is a small neutral helper for building approval tool metadata from Agent plans so future write execution paths can reuse the same gate without importing `tool_executor.py`.
