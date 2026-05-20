# Phase54 Report: Context Diagnostics Recovery

## Summary

Phase54 makes the Phase52/53 longform context summary actionable inside the Writing Agent run loop.

When `summarize_longform_context` detects stale or missing longform memory/retrieval maintenance, an auto-planned chapter run now stops before `generate_chapter`, records a structured decision, and recommends the concrete repair tool `repair_longform_maintenance`.

When maintenance is healthy, the same context gate remains transparent and the normal path continues to `preflight_writing` and generation.

## Reference Assimilation

The implementation adapts three reference patterns:

- `openclaw`: route decisions should be explicit data, not implicit prompt text. novelv3 now emits `decision`, `should_generate_next_chapter`, and `recommended_actions`.
- `hermes-agent`: only hard blockers should stop the run. novelv3 blocks only when longform memory/retrieval maintenance is not ready; context truncation remains diagnostic-only.
- `openhuman`: memory recall should stay read-only while repair is an explicit write operation. novelv3 keeps `summarize_longform_context` read-only and exposes `repair_longform_maintenance` as a separate Agent tool.

Not copied:

- OpenClaw generic hook/runtime routing system.
- Hermes broad assistant fallback flow.
- OpenHuman external memory daemon or separate memory backend.

## Changes

- Updated `backend/app/services/writing_agent/longform_context_summary.py`.
  - Adds `decision`, `should_generate_next_chapter`, and `recommended_actions`.
  - Reports `longform_memory_needs_maintenance` when maintenance is stale.
- Updated `backend/app/services/writing_agent/tool_registry.py`.
  - Registers internal write tool `repair_longform_maintenance`.
- Updated `backend/app/services/writing_agent/tool_executor.py`.
  - Adds a static adapter for `repair_longform_maintenance`.
  - Normalizes repair output to JSON-safe data before step persistence.
- Updated `backend/app/services/writing_agent/run_service.py`.
  - Lets `summarize_longform_context` stop follow-up generation when it returns `should_generate_next_chapter=false`.
- Updated `backend/app/services/writing_agent/recovery_policy.py`.
  - Converts blocked context diagnostics into a recovery recommendation.
- Updated `backend/app/services/writing_agent/recovery_planner.py`.
  - Lets recovery preview find successful diagnostic steps inside blocked runs.
  - Marks `repair_longform_maintenance` as safe for recovery execution preview.
- Updated tests in:
  - `backend/tests/test_writing_agent_runs.py`
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_tool_registry.py`
- Added plan:
  - `docs/superpowers/plans/long-memory-agent/2026-05-20-phase54-context-diagnostics-recovery.md`

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or repair_longform_maintenance"
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "repair_longform_maintenance"
```

Observed before implementation:

- stale context run returned `success` instead of `blocked`;
- `repair_longform_maintenance` direct Agent run failed because the tool was not registered/adapted;
- registry/executor tests failed because the descriptor and adapter did not exist.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or repair_longform_maintenance"
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "repair_longform_maintenance"
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "auto_plan_executes_high_level_next_chapter_goal"
```

Result:

- context block/repair API: `2 passed, 126 deselected`.
- registry/executor repair checks: `3 passed, 16 deselected`.
- healthy auto-plan path: `1 passed, 127 deselected`.

T1 Agent verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `151 passed in 9.68s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` completed with only the existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Boundary

Phase54 only handles one deterministic hard blocker: stale longform memory/retrieval maintenance. It does not yet make the Agent dynamically re-plan across all diagnostics or auto-run repairs without an explicit recovery step.

## Novel Progress

No new longform novel chapter was generated in this phase. The phase focused on making chapter generation safer by preventing generation when context maintenance is stale.

## Next Recommendation

Phase55 should continue toolizing existing modules into Agent-callable capabilities. The next useful step is to expose a structured "context readiness repair sequence" that can chain:

- `repair_longform_maintenance`;
- `summarize_longform_context`;
- `preflight_writing`;
- then generation only when all hard blockers are clear.

This keeps moving the system from fixed plans toward diagnostics-driven orchestration without requiring the user to encode chapter constraints manually.
