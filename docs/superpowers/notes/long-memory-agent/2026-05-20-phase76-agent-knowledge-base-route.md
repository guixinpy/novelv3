# Phase76 Report: Agent Knowledge Base Route

## Summary

Phase76 adds the first read-only Knowledge Base projection tool for the Writing Agent: `inspect_agent_knowledge_base_route`.

This is a minimum domain-specific long-memory route. It does not create a new storage layer yet. Instead, it projects the project’s existing creative memory sources into one Agent-readable contract:

- author preferences from `Project.style_config`;
- project strategy from `Project` metadata;
- learned self-optimization rules from `PromptRule(rule_type="learned")`;
- reference/writing pattern availability from `FewShotExampleLibrary`;
- diagnostics that keep Knowledge Base separate from Athena world truth.

## Why This Matters

The goal document defines Knowledge Base as the Agent’s long-term creative memory: author preferences, project strategy,拆书/writing patterns, and self-optimization experience. Before this phase, these signals existed in separate places and were not exposed as one Agent tool.

This phase makes the Agent less dependent on operator-written detailed prompts. The planner can now include a Knowledge Base read before longform context and chapter generation.

## Changes

- Added `backend/app/services/writing_agent/agent_knowledge_base_route.py`.
- Added `inspect_agent_knowledge_base_route` to the Writing Agent tool registry.
- Added executor adapter `_inspect_agent_knowledge_base_route`.
- Added the Knowledge Base route to the `continue_next_chapter` planner chain before `summarize_longform_context`.
- Added service-level tests for:
  - sparse project creative memory;
  - configured preferences, project strategy, learned rules, and reference patterns;
  - bounded learned-rule windows.
- Updated registry, executor, planner, and Agent run tests.

## Result Contract

Sparse project:

```json
{
  "route": {
    "status": "sparse",
    "reason": "knowledge_base_sparse",
    "recommended_tools": ["summarize_longform_context", "preflight_writing", "review_chapter_quality"]
  },
  "author_preferences": {
    "status": "empty"
  },
  "learned_rules": {
    "total": 0
  }
}
```

Configured project:

```json
{
  "route": {
    "status": "ready",
    "reason": "knowledge_base_available"
  },
  "author_preferences": {
    "status": "configured"
  },
  "project_strategy": {
    "target_chapter_count": 600
  },
  "learned_rules": {
    "total": 1
  },
  "trace": {
    "mutability": "read"
  }
}
```

Boundary diagnostic:

```json
{
  "code": "world_truth_boundary",
  "severity": "info",
  "message": "知识库是作者偏好、项目策略和写法经验，不是 Athena 世界真相；内部事实仍需走世界模型和提案机制。"
}
```

## Verification

RED before implementation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "knowledge_base_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result before implementation: collection failed because `app.services.writing_agent.agent_knowledge_base_route` did not exist.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "knowledge_base_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

Result: `8 passed, 53 deselected in 0.32s`.

Related preference/self-optimization/tool regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_preferences.py tests\test_self_optimization.py -q
```

Result: `70 passed in 1.95s`.

Planner/auto-plan regression after adding the route to the continuation chain:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_planner.py tests\test_writing_agent_runs.py -q -k "planner_builds_ready_next_chapter_tool_chain or planner_adds_outline_expansion or auto_plan"
```

Result: `7 passed, 151 deselected in 1.47s`.

Broader related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_knowledge_base_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_planner.py tests\test_preferences.py tests\test_self_optimization.py tests\test_writing_agent_runs.py -q
```

Result: `228 passed in 18.85s`.

All Writing Agent related tests:

```powershell
cd backend
$files = Get-ChildItem tests -Filter "test_writing_agent_*.py" | ForEach-Object { $_.FullName }; .venv\Scripts\python.exe -m pytest @files tests\test_athena_ontology_agent.py -q
```

Result: `231 passed in 17.97s`.

## Novel Progress

No production novel chapter was generated in this phase.

Reason: this phase adds the missing Knowledge Base projection to the pre-generation Agent chain. The next dogfood generation should use the toolchain:

1. `inspect_agent_knowledge_base_route`
2. `inspect_agent_memory_route`
3. `inspect_agent_world_model_route`
4. `inspect_agent_job_projection`
5. `summarize_longform_context`
6. `preflight_writing`

## Fixed Issues

- Agent had no unified creative-memory view for author preferences, project strategy, learning rules, and reference patterns.
- Auto-planned continuation runs did not read creative long-term memory before context summary and generation.
- Knowledge Base / world truth boundary was implicit rather than visible to Agent output.

## Remaining Boundary

This phase is read-only. It does not:

- add a Knowledge Base table;
- add a frontend memory management UI;
- extract new memories from user chat automatically;
- ingest拆书 results;
- write Athena world facts or proposals;
- call an LLM.

Recommended next phases:

1. Resume dogfood generation using the expanded pre-generation toolchain and record whether low-detail user intent is enough for Agent-led chapter planning.
2. Add a write-side Knowledge Base candidate tool only after one or two dogfood loops show which memory items need persistence.
3. Start a small拆书 pattern contract that stores abstract structural lessons without retaining copyrighted prose.
