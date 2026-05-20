# Phase46 Report: Backfill Tool Adapter

## Phase Goal

Migrate one mutation-light maintenance tool, `backfill_outline_gaps`, from `run_service.py` into the Writing Agent executor adapter map.

## Implemented

- Added `_backfill_outline_gaps` adapter in `tool_executor.py`.
- Registered `backfill_outline_gaps` with metadata:
  - `category: maintenance`;
  - `mutability: write`;
  - `adapter_type: static`.
- Moved parameter normalization into the executor adapter:
  - `before_chapter` wins when present;
  - falls back to `chapter_index`;
  - missing bound passes `None`.
- Removed the old run-service branch.
- Updated migration diagnostics so `backfill_outline_gaps` is no longer listed as unhandled internal tooling.

## Why This Helps Agentization

This is the first write-capable maintenance adapter in the executor map. It proves the tool layer can handle small state-changing maintenance tools while keeping run lifecycle and blocking behavior in `run_service.py`.

It also reduces the remaining legacy dispatcher surface without touching high-risk generation, revision, or world-model apply flows.

## Validation

Validation level: T1.

Focused RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q -k "backfill"
```

RED result:

```text
2 failed; metadata was None and executor returned handled=False
```

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q -k "backfill"
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_backfill_outline_gaps_uses_existing_chapter_content_then_preflight_ready -q
```

Result:

```text
2 passed, 9 deselected
1 passed
```

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result:

```text
134 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: exit 0
secret scan: exit 1; no matches
```

## Current Limits

- Larger write tools remain in `run_service.py`.
- The executor does not yet support async adapters.
- `preflight_writing` remains injected because it still depends on run-service private checks.

## Next Phase Recommendation

Phase47 should avoid rushing high-risk migrations. The better next step is either:

- add adapter kinds for legacy run-service/action-service branches in `agent_tool_result`; or
- introduce a recovery policy reader that consumes `agent_tool_result` and planner failure metadata for blocked preflight and missing outline cases.
