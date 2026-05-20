# Phase76 Plan: Agent Knowledge Base Route

## Phase Goal

Add a minimum read-only Knowledge Base route for the Writing Agent.

This phase gives the Agent one compact tool for inspecting creative long-term memory that is separate from Athena world truth:

- author preferences from `Project.style_config`;
- project strategy from `Project` metadata;
- learned self-optimization rules from `PromptRule`;
- reference/writing pattern availability from the few-shot library;
- boundary diagnostics that remind the Agent not to treat Knowledge Base items as world facts.

## Novel Work

No new production chapter will be generated in this phase.

Reason: the previous phases just added memory, trace, world-model, and job projection tools. Before resuming dogfood generation, the Agent needs a Knowledge Base projection so the pre-generation toolchain can read author/project creative memory without relying on operator-written prompts.

## System Capability

Add `inspect_agent_knowledge_base_route` as an internal, non-blocking Writing Agent report tool.

The tool should:

- be read-only;
- require only an existing project;
- return stable sections for `author_preferences`, `project_strategy`, `learned_rules`, `reference_patterns`, `diagnostics`, and `route`;
- preserve the boundary between creative memory and world truth;
- recommend the next tool based on gaps:
  - if no learned rules or preferences exist, recommend continuing generation/review and recording feedback later;
  - if knowledge exists, recommend `summarize_longform_context` and `preflight_writing` for generation flows.

## Modules

- `backend/app/services/writing_agent/agent_knowledge_base_route.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/app/services/writing_agent/tool_executor.py`
- `backend/tests/test_writing_agent_knowledge_base_route.py`
- existing registry/executor tests

## Verification Level

T1 local backend verification.

Planned checks:

1. RED focused tests for the new service and registry/executor contract.
2. GREEN focused tests for the new service and registry/executor contract.
3. Related Writing Agent tests:
   - `test_writing_agent_knowledge_base_route.py`
   - `test_writing_agent_tool_registry.py`
   - `test_writing_agent_tool_executor.py`
   - `test_preferences.py`
   - `test_self_optimization.py`
4. All Writing Agent related tests if the local focused suite is stable.

## Risks

- Mixing Knowledge Base with Athena truth would weaken world-model governance.
- Adding a database table now could over-expand scope before the route contract is proven.
- Injecting too many learned rules into every generation turn could pollute context.

## Not Doing

- No new database schema.
- No frontend Knowledge Base page.
- No automatic preference extraction from arbitrary user chat.
- No world-model writes.
- No API key usage or LLM calls.
