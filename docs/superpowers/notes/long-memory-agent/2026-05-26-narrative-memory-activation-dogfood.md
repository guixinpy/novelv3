# Narrative Memory Activation Dogfood

Date: 2026-05-26
Branch: `codex/narrative-memory-activation`

## Purpose

Verify the next long-memory Agent slice: before writing a target chapter, the
Agent should activate prior longform memory and open foreshadowing, exclude
future memory, inject a bounded prompt block into generation, then refresh
longform memory so the next chapter can reuse the newly written events.

## Focused Verification

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py backend\tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_memory_activation_without_future_leak backend\tests\test_writing_agent_runs.py::test_agent_preflight_reports_memory_activation_plan backend\tests\test_writing_agent_runs.py::test_refresh_longform_memory_prefers_reviewed_event_summary_proposal backend\tests\test_writing_agent_health_projection.py::test_inspect_agent_health_projection_reports_memory_activation_debt -q
# 6 passed
```

## API-Backed Dogfood

Environment: isolated in-memory SQLite through FastAPI `TestClient`, with
`ActionExecutionService.execute` patched to avoid real model calls while still
going through `/api/v1/projects/{project_id}/agent-runs`, tool execution,
preflight, activation, generation, review, memory repair, and health projection.

- Project: `37964dae-c9bf-4fa3-adfc-44cee18ca52a`
- Agent run: `e122d31b-d1ad-4e0d-9a4c-639a45b169ba`
- Generation trace: `75137b86-89d7-498d-95bf-843dfcc7004e`

Steps:

1. `preflight_writing` chapter 3 -> `ready`
2. `inspect_agent_memory_activation_plan` chapter 3 -> `degraded`
3. `generate_chapter` chapter 3 -> `success`
4. `review_chapter_quality` chapter 3 -> `ready`
5. `review_chapter_continuity` chapter 3 -> `ready`
6. `repair_longform_maintenance` -> `completed`
7. `inspect_agent_memory_activation_plan` chapter 4 -> `ready`
8. `inspect_agent_health_projection` chapter 4 -> `degraded`

Key evidence:

- Chapter 3 activation selected 3 longform items and open foreshadowing
  `空白信来源`.
- Chapter 3 activation prompt included `空白信`.
- Chapter 3 activation prompt did not include future-only `潮下车站`.
- Generation output recorded activation provenance with `source_count=5`.
- Memory repair refreshed 1 memory and 6 retrieval documents.
- Chapter 4 activation became `ready`.
- Chapter 4 activation included the newly generated chapter 3 memory
  `记忆激活第3章`.
- Health projection reported `memory_activation_status=ready`; the remaining
  degraded status came from existing `agent_write_gate_high_risk`, not memory
  activation.

## Result

This slice proves the Agent can use long-memory as an active writing surface:
prior clues are selected before generation, future leaks are excluded, generated
chapter output carries activation provenance, and memory repair makes the new
chapter available to the next activation cycle.

## Final Verification

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_activation.py backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py -q
# 17 passed

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify_local_quality.ps1
# Backend pytest: 1358 passed
# Frontend unit: 567 passed
# Frontend build: passed
```

Skipped by the existing verification script:

- Workspace perf smoke: missing `PERF_SMOKE_BASE_URL`,
  `PERF_SMOKE_PROJECT_ID`, and `PERF_SMOKE_SESSION`.
- Frontend E2E: `-RunE2E` / `RUN_E2E=1` was not enabled.

Non-blocking residue: the full quality script exited `0`; pytest emitted one
ignored Windows `PermissionError` while cleaning a temp directory at atexit.
