# Phase67 Report: Athena Ontology Agent Entrypoint

## Summary

Phase67 migrates the first non-dialog, real UI-facing generation entrypoint into the Agent Service control plane.

`POST /api/v1/projects/{project_id}/athena/ontology/generate`, used by the frontend setup generation button, no longer calls the legacy setup generator directly. It now creates a `WritingAgentRun(entrypoint="athena_ontology_generate")`, executes the `generate_setup` tool, and returns the existing setup payload plus compact Agent provenance metadata.

The low-level `backend/app/api/setups.py::generate_setup` remains the current Hermes setup tool implementation. This avoids recursion and keeps the migration incremental.

## Reference Assimilation

Adopted:

- `openclaw`: UI actions should enter a control-plane run abstraction instead of directly calling feature code.
- `hermes-agent`: tool execution should leave durable run and step records.
- `openhuman`: user-facing responses should stay compact while provenance is stored in structured records.

Not adopted:

- migrating `/setup/generate` itself;
- migrating chapter generation or continuous writing;
- adding frontend Agent run panels;
- replacing setup prompt/schema.

## Changes

- Added `backend/tests/test_athena_ontology_agent.py`.
- Updated `backend/app/api/athena_ontology.py`.
- Added Agent control-plane constants:
  - `phase67.athena_ontology_agent.v1`
  - `athena_ontology_generate`
- `generate_ontology()` now:
  - validates the project;
  - creates `WritingAgentRun` with `generate_setup`;
  - executes the run synchronously;
  - returns generated setup fields plus `agent_run_id` and `control_plane`;
  - preserves missing API key as HTTP 400.

## Control Plane Contract

Entrypoint:

- `athena_ontology_generate`

Control plane version:

- `phase67.athena_ontology_agent.v1`

Tool:

- `generate_setup`

Response keeps existing setup fields and adds:

```json
{
  "agent_run_id": "<run-id>",
  "control_plane": {
    "version": "phase67.athena_ontology_agent.v1",
    "source": "athena_ontology_generate"
  }
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_ontology_agent.py -q -k "ontology_generate"
```

Result before implementation: `1 failed, 1 passed`; failure confirmed no `WritingAgentRun` existed for the Athena ontology generate entrypoint.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_ontology_agent.py -q -k "ontology_generate"
```

Result: `2 passed in 0.29s`.

T1/T2 related backend regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_athena_ontology_agent.py tests\test_setups.py tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py -q
```

Result: `191 passed in 23.98s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This phase moved a real setup-generation entrypoint into Agent Service, which is required before using the app itself for long-running low-detail user-driven novel generation.

## Discovered Issues

- The frontend setup generation button used Athena ontology generate, which still bypassed `WritingAgentRun`.
- Existing direct wrappers made the app look Agent-capable only through dialog confirmation, while normal UI buttons still executed modules directly.

## Fixed Issues

- Athena setup generation now creates a durable Agent run and step.
- The generated setup remains frontend-compatible.
- Missing API key behavior remains HTTP 400.
- Agent provenance is visible in the response without requiring frontend changes.

## Remaining Boundary

The project is still not fully Agent Service based. Remaining high-value migrations:

- Athena evolution/storyline and outline generate wrappers;
- direct chapter generation API;
- continuous writing start/resume and retry task creation;
- frontend display of Agent run provenance;
- tool adapter extraction so legacy generators become cleaner tool implementations instead of being called through API modules.

The next phase should migrate another real UI/API entrypoint, preferably Athena evolution plan generation or continuous writing planning, while keeping the migration small enough for targeted verification.
