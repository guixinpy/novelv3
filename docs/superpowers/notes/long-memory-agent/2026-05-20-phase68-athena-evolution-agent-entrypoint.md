# Phase68 Report: Athena Evolution Agent Entrypoint

## Summary

Phase68 migrates Athena evolution plan generation into the Agent Service control plane.

`POST /api/v1/projects/{project_id}/athena/evolution/plan/generate?target=storyline|outline`, used by the frontend story line and outline generation actions, now creates and executes a `WritingAgentRun(entrypoint="athena_evolution_plan_generate")` with `generate_storyline` or `generate_outline`.

This continues the whole-project Agent Service migration beyond slash commands and ordinary chat text. Normal UI/API generation actions are now becoming Agent-controlled entrypoints.

## Reference Assimilation

Adopted:

- `openclaw`: UI/API intents normalize into control-plane tool calls.
- `hermes-agent`: generation tool calls are represented by durable runs and steps.
- `openhuman`: API responses remain compact while execution provenance is preserved.

Not adopted:

- direct `/storyline/generate` and `/outline/generate` migration;
- chapter generation migration;
- continuous writing migration;
- frontend Agent run panel.

## Changes

- Added `backend/app/services/writing_agent/api_control_plane.py`.
- Refactored Phase67 `athena_ontology.generate_ontology()` to reuse the shared API control-plane helper.
- Updated `backend/app/api/athena_evolution.py`:
  - `target=storyline` now executes `generate_storyline` via Agent run;
  - `target=outline` now executes `generate_outline` via Agent run;
  - `response_mode=window` and `response_mode=full` remain supported;
  - known legacy validation errors remain HTTP 400;
  - responses include `agent_run_id` and `control_plane`.
- Extended `backend/tests/test_athena_evolution_generation_windows.py` with Agent run/step assertions and missing API key compatibility.

## Control Plane Contract

Entrypoint:

- `athena_evolution_plan_generate`

Control plane version:

- `phase68.athena_evolution_agent.v1`

Targets:

- `storyline` -> `generate_storyline`
- `outline` -> `generate_outline`

Response metadata:

```json
{
  "agent_run_id": "<run-id>",
  "control_plane": {
    "version": "phase68.athena_evolution_agent.v1",
    "source": "athena_evolution_plan_generate",
    "action_type": "generate_outline",
    "target": "outline"
  }
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_evolution_generation_windows.py -q
```

Result before implementation: `2 failed, 1 passed`; failures confirmed no `WritingAgentRun` existed for storyline/outline Athena evolution generation.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_evolution_generation_windows.py tests\test_athena_ontology_agent.py -q -k "generate"
```

Result: `5 passed in 0.69s`.

T1/T2 related backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_evolution_generation_windows.py tests\test_athena_ontology_agent.py tests\test_storylines.py tests\test_outlines.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py -q
```

Result: `211 passed in 29.31s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This phase continues prerequisite Agent Service migration so future real novel generation can be driven through unified Agent runs instead of scattered module endpoints.

## Discovered Issues

- Athena evolution generation still bypassed `WritingAgentRun`.
- Phase67 introduced a useful pattern, but the API control-plane logic was local to ontology generation.
- Existing windowed generation tests proved response scaling, but did not require execution provenance.

## Fixed Issues

- Storyline generation through Athena now creates Agent run and step records.
- Outline generation through Athena now creates Agent run and step records.
- The shared API control-plane helper centralizes synchronous API-to-Agent tool execution.
- Existing frontend-compatible windowed responses remain intact.
- Missing API key behavior remains HTTP 400.

## Remaining Boundary

The project is still not fully Agent Service based. Remaining migration targets:

- direct `/storyline/generate`, `/outline/generate`, and `/chapter/generate` endpoints;
- continuous writing `/writing/start`, `/writing/resume`, and retry task paths;
- frontend display and polling of Agent run provenance;
- tool adapter extraction so Agent tools no longer call API modules internally;
- real longform generation dogfood once the main generation pathways consistently enter Agent control plane.

Next phase should either migrate direct chapter generation or start converting continuous writing queue tasks to create and execute Agent runs.
