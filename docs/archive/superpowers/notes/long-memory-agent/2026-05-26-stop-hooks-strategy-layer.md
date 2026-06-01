# 2026-05-26 StopHooks Strategy Layer Slice

## Goal Link

Active goal: complete the full Agent-native long-memory writing Agent upgrade from `docs/agent-native-guide/01-reference-patterns-report.md`.

This note covers Task 3 from `docs/superpowers/plans/2026-05-26-agent-native-long-memory-writing-agent.md`: extract an equivalent StopHooks strategy layer.

## Implemented

- Added `agent_stop_hooks.py` with `evaluate_agent_stop_hooks(run, steps, latest_output)`.
- Stop decisions now project four independently testable hooks:
  - critical loop risk
  - missing approval contract
  - blocked/recoverable memory provenance
  - open context guard
- `run_service` now includes `agent_loop.stop_hooks` in continuation state.
- Existing run behavior is preserved; this slice adds a strategy projection rather than changing execution order.

## Evidence

Focused tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_stop_hooks.py -q
# 4 passed
```

Run-service integration:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_output_exposes_agent_loop_contract_for_success -q
# 1 passed

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_loop_stop_hooks_block_critical_loop_risk -q
# 1 passed
```

Related regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_stop_hooks.py backend\tests\test_writing_agent_runs.py -k "agent_loop or stop_hooks or provenance" -q
# 12 passed, 178 deselected

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py backend\tests\test_writing_agent_memory_provenance_contract.py -q
# 17 passed
```

Static diff check:

```powershell
git diff --check
# no output
```

## Remaining

- StopHooks currently project decisions; later slices can make the run loop consume them as execution gates where behavior tests prove equivalence.
- Missing approval detection is reason-code based; future approval-contract refactors should move those codes into a shared constant module.
- ContextGuard failure count is still supplied by the context projection slice; future tool lifecycle/event slices should derive it from run history.

