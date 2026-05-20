# Phase77 Plan: Dogfood Pre-Generation Route

## Phase Goal

Resume the real `《雾港回声》` dogfood loop after the Agent infrastructure phases by running a generation-readiness route on the live dogfood project.

This phase checks whether the Agent can now assemble its own writing context from tools instead of depending on detailed operator prompts.

## Novel Work

Target: Chapter 24.

Expected mode:

- first run read-only generation readiness tools;
- generate Chapter 24 only if the route is ready;
- if blocked, document the blocker and fix the smallest system issue that prevents autonomous continuation.

## System Capability Under Test

Pre-generation Agent toolchain:

1. `inspect_agent_knowledge_base_route`
2. `inspect_agent_memory_route`
3. `inspect_agent_world_model_route`
4. `inspect_agent_job_projection`
5. `summarize_longform_context`
6. `preflight_writing`

The main question: can a low-detail user intent such as “继续写下一章” produce enough structured context for a stable next chapter?

## Verification Level

T2 dogfood route verification.

Planned checks:

- direct database/project state inspection;
- read-only toolchain execution against the live dogfood DB;
- if generation runs, post-generation quality/continuity/world-model/maintenance checks;
- targeted backend tests only for code changes exposed by this phase.

## Risks

- Live dogfood DB has historically had stale migration metadata.
- Longform memory and retrieval may be current, but new planner tools may expose older assumptions.
- If the route blocks, the correct output is a documented blocker, not forcing generation with manual constraints.

## Not Doing

- No broad refactor unless a concrete dogfood blocker requires it.
- No full frontend test pass unless this phase touches frontend.
- No manual long chapter prompt; the Agent must rely on project state and tools.
- No API key written to disk.
