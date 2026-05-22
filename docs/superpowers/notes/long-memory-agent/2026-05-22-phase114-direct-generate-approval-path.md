# Phase114 Direct Generate Approval Path Report

## Phase Summary

Phase114 added an Agent-native approved path for direct chapter generation without changing the existing `generate_chapter` adapter or chapter API behavior.

The new flow is:

1. `prepare_generate_chapter_execution`
2. user/Agent receives the approval contract hash
3. `execute_generate_chapter_with_approval`
4. approval contract verification
5. chapter generation implementation runs

## Goal Alignment

- Moves manuscript mutation toward explicit Agent plan approval gates.
- Avoids breaking existing API/front-end chapter generation while adding a safer Agent-native route.
- Builds on Phase112/113 by reusing approval metadata projection and exposing the new route in write gate coverage.

## Implemented

- Added `chapter_generation_execution.py`.
- Added `prepare_generate_chapter_execution`.
- Added `execute_generate_chapter_with_approval`.
- Registered both tools in the Agent tool registry.
- Added static executor adapters for both tools.
- Updated write gate coverage:
  - `execute_generate_chapter_with_approval` is `enforced`.
  - `generate_chapter` now reports indirect Agent-gated coverage via both batch execution and the new direct approved execute path.
- Preserved existing `generate_chapter` behavior for API compatibility.

## Boundary Decision

This phase does not migrate dialog planner or slash command routing to the new prepare/execute pair. Current direct routes remain unchanged so existing workflows keep working.

Planner migration should happen in a later phase after UI/API handling for approval-required tool flows is explicitly checked.

## Novel Progress

No new novel chapter was generated in this phase. This phase hardens the Agent execution layer used by future autonomous long-running generation.

## Verification

RED service test:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_chapter_generation_execution.py -q
```

Initial result:

```text
ModuleNotFoundError: No module named 'app.services.writing_agent.chapter_generation_execution'
```

Focused GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_chapter_generation_execution.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_write_gate_coverage.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "generate_chapter_with_approval or prepare_generate_chapter_execution or approved_direct_chapter or write_gate_coverage" -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py -q
```

Result:

```text
4 passed
5 passed
5 passed, 74 deselected
32 passed
```

T1 related coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_chapter_generation_execution.py backend/tests/test_writing_agent_write_gate_coverage.py backend/tests/test_writing_agent_approval_tool_metadata.py backend/tests/test_writing_agent_approval_contract.py backend/tests/test_writing_agent_tool_registry.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "approval_contract or execute_longform_chapter_batch or generate_chapter" -q
```

Result:

```text
57 passed
79 passed
10 passed, 160 deselected
```

During T1, one executor test failed because the test expected dialog planner routes to already use the new prepare/execute pair. That expectation was incorrect for this phase and was reverted. Planner migration remains intentionally out of scope.

## Next Phase Recommendation

Phase115 should add a read-only route/intent projection that tells the Agent when to prefer `prepare_generate_chapter_execution` over direct `generate_chapter`, without yet changing runtime execution behavior. After that, a controlled planner migration can be tested.
