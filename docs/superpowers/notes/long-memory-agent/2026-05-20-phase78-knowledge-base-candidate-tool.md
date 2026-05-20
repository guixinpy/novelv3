# Phase78 Report: Knowledge Base Candidate Tool

## Summary

Phase78 adds the first write-side Knowledge Base tool for the Writing Agent: `record_agent_knowledge_base_candidate`.

This phase addresses the Phase77 finding that the dogfood project’s Knowledge Base route was visible but sparse. The new tool lets the Agent persist creative-memory candidates from real writing evidence without touching Athena world truth.

## Design

Storage is intentionally conservative:

- candidates are stored under `Project.style_config["knowledge_base_candidates"]`;
- no database schema or migration was added;
- candidate shape is explicit enough to migrate later to a dedicated Knowledge Base table.

This avoids the local dogfood DB migration risk while allowing real Agent learning to begin.

## Candidate Contract

Each candidate includes:

- `id`
- `fingerprint`
- `memory_type`
- `title`
- `summary`
- `source_refs`
- `confidence`
- `status`
- `tags`
- `created_at`
- `updated_at`
- `observed_count`

Initial memory types:

- `author_preference`
- `project_strategy`
- `writing_pattern`
- `self_optimization_lesson`
- `decomposition_pattern`

Initial statuses:

- `candidate`
- `active`
- `muted`
- `rejected`

## Changes

- Added `backend/app/services/writing_agent/agent_knowledge_base_candidates.py`.
- Updated `inspect_agent_knowledge_base_route`:
  - excludes `knowledge_base_candidates` from author preference facets;
  - exposes `knowledge_candidates`;
  - treats existing candidates as enough to avoid `knowledge_base_sparse`;
  - reports `knowledge_candidates_truncated` when the route window is bounded.
- Added `record_agent_knowledge_base_candidate` to the Writing Agent tool registry.
- Added executor adapter `_record_agent_knowledge_base_candidate`.
- Added tests for:
  - candidate creation;
  - deduplication by fingerprint;
  - source-ref validation;
  - read route candidate projection;
  - registry contract;
  - executor metadata and dispatch.

## Runtime Dogfood Write

Recorded one live candidate for `《雾港回声》`:

```json
{
  "memory_type": "self_optimization_lesson",
  "title": "低细节续写需要先走 Agent 生成前路线",
  "source_refs": [
    "docs/superpowers/notes/long-memory-agent/2026-05-20-phase77-dogfood-pre-generation-route.md",
    "agent-run:2928c80b-206d-4740-afb7-73567f3202ab",
    "chapter:24"
  ],
  "confidence": 0.9
}
```

Result:

- status: `completed`
- action: `created`
- candidate count: `1`

Read route after write:

- route status: `ready`
- reason: `knowledge_base_available`
- knowledge candidate total: `1`
- diagnostics: `world_truth_boundary`

This confirms the Knowledge Base is no longer sparse for the dogfood project.

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "knowledge_base_candidate or knowledge_base_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result before implementation: collection failed because `app.services.writing_agent.agent_knowledge_base_candidates` did not exist.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "knowledge_base_candidate or knowledge_base_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result: `14 passed, 53 deselected in 0.58s`.

Related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_planner.py tests\test_preferences.py tests\test_self_optimization.py tests\test_writing_agent_runs.py -q
```

Result: `234 passed in 20.31s`.

All Writing Agent related tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

Result: `237 passed in 18.20s`.

Runtime dogfood write:

```powershell
cd backend
.venv\Scripts\python.exe - <<'PY'
# record_agent_knowledge_base_candidate
# inspect_agent_knowledge_base_route
PY
```

Result:

- record: `completed / created`
- route: `ready / knowledge_base_available`

## Novel Progress

No new chapter was generated in this phase.

Latest dogfood state remains:

- latest generated chapter: `24`
- latest title: `雾中栖身`
- latest word count: `2436`
- next target: Chapter 25

## Fixed Issues

- Agent had no write-side path for creative-memory candidates.
- Knowledge Base route could reveal sparse state but could not be improved by Agent action.
- `Project.style_config` preference projection would have treated internal candidate storage as a preference facet; this is now excluded.

## Remaining Boundary

This is a bridge implementation. It does not:

- add a first-class Knowledge Base table;
- expose candidate management UI;
- automatically extract candidates from chat or chapters;
- inject all candidates into prompts;
- mark candidates as user-approved;
- write Athena world facts.

## Next Phase Recommendation

Phase79 should decide how candidates enter generation context.

Recommended minimum:

- update `inspect_agent_knowledge_base_route` or the planner to surface only relevant candidate summaries for the target chapter;
- avoid dumping all candidates into prompts;
- add status filtering so only `active` or high-confidence `candidate` items influence generation;
- use Chapter 25 dogfood generation to verify that the new lesson is visible without overloading context.
