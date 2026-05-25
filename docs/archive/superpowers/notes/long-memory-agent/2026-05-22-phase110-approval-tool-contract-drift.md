# Phase110 Approval Tool Contract Drift Report

## Phase Summary

Phase110 extends the read-only approval verification preflight with live tool-contract drift checks for write steps. The verifier now reports whether each approved write step still points to an existing Agent tool, has an execution adapter, still has write/guarded-write mutability, still requires confirmation, and contains required input schema fields in step params.

## Goal Alignment

- Advances the Writing Agent control plane from `plan -> approval hash` toward `plan -> approval hash -> live tool-contract safety check`.
- Keeps Hermes/Athena/task-queue capabilities moving toward Agent-callable tools with auditable contracts.
- Preserves the goal constraint that approval verification is read-only and must not execute write tools.

## Implemented

- Added optional `tool_metadata_by_name` input to `verify_agent_plan_approval_contract()`.
- Added per-write-step drift reporting:
  - `tool_exists`
  - `adapter_exists`
  - `current_mutability`
  - `current_requires_confirmation`
  - `required_fields`
  - `missing_required_fields`
  - `status`
  - `reasons`
- Added drift summary fields:
  - `tool_contracts_checked`
  - `tool_contract_drift_count`
  - `tool_contracts`
- Blocks verified approval contracts with `reason == "tool_contract_drift"` when live tool metadata shows drift.
- Recommends `inspect_agent_tool_contracts` for tool-contract drift recovery.
- Added executor-side metadata injection from registry descriptors, static adapter metadata, and `agent_tool_execution_metadata()`.

## Boundary Decision

`approval_contract.py` remains a pure contract/verifier module. It does not import `tool_executor.py` or query the registry directly. `tool_executor.py` owns the runtime projection of descriptors/adapters and passes the narrow metadata dict into the verifier.

This keeps dependency direction clear:

```text
tool_executor adapter -> tool_registry/tool_contracts -> approval_contract pure verifier
```

## Subagent Review

A read-only architecture subagent reviewed the phase boundary and recommended:

- Keep approval verification read-only.
- Avoid direct `approval_contract.py -> tool_executor.py` dependency.
- Pass narrow tool metadata into the verifier.
- Check only low-cost live-state drift.
- Do not add full JSON Schema validation, DB availability checks, handler signature checks, or full tool-contract snapshot hashing in this phase.

The implementation follows those constraints.

## Novel Progress

No novel chapter was generated in this phase. This phase improves the approval-control safety needed before autonomous long-running chapter generation can execute write chains.

## Verification

RED unit tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -q
```

Initial result:

```text
3 failed, 8 passed
TypeError: verify_agent_plan_approval_contract() got an unexpected keyword argument 'tool_metadata_by_name'
```

RED executor test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "approval_contract_verification" -q
```

Initial result:

```text
1 failed, 73 deselected
KeyError: 'tool_contracts_checked'
```

Focused green results:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "approval_contract_verification" -q
```

Result:

```text
12 passed
1 passed, 73 deselected
```

T1 module coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

```text
116 passed
```

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

```text
git diff --check: no output
secret scan: no matches
```

## Next Phase Recommendation

Phase111 should connect approval verification evidence to the next controlled execution path instead of expanding verifier scope. A good target is to make a future write execution adapter require both the approved contract hash and a fresh `verify_agent_plan_approval_contract` ready result before executing selected write steps, still keeping preview/verify read-only and execution-gate logic separate.
