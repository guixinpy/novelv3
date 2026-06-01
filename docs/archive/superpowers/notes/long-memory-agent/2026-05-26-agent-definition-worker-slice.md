# 2026-05-26 AgentDefinition Worker Slice

## Goal Link

Active goal: complete the full Agent-native long-memory writing Agent upgrade from `docs/agent-native-guide/01-reference-patterns-report.md`.

This note covers Task 5 from `docs/superpowers/plans/2026-05-26-agent-native-long-memory-writing-agent.md`: introduce repo-local AgentDefinition config and read-only worker dispatch preview.

## Implemented

- Added `agent_definitions.py` to load repo-local YAML worker definitions.
- Added `agent_definitions/reviewer.yaml` with explicit `name`, `role`, `max_depth`, `allowed_tools`, and `write_policy`.
- Added `agent_worker_dispatch.py` with `preview_agent_worker_dispatch(...)`.
- Reviewer worker preview is read-only: it returns planned task envelopes, never executes tools or LLM calls, and blocks child dispatch or tools outside its allowlist.

## Evidence

Focused tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_agent_definitions.py -q
# 3 passed
```

## Remaining

- Existing profile projection constants still exist; future slices should consume AgentDefinition config directly where policy decisions need config-backed workers.
- This slice exposes dispatch as a service function only. A later agent-tool adapter can make it model-callable once the desired control-plane surface is clear.
