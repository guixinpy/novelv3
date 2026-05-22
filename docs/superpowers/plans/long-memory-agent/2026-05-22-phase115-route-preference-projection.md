# Phase115 Route Preference Projection Plan

## Objective

Add a read-only route preference projection that tells the Agent when chapter-generation intents should prefer the approved `prepare_generate_chapter_execution -> execute_generate_chapter_with_approval` path while leaving existing dialog and slash command runtime routes unchanged.

## Assumptions

- Phase114 added the approved direct chapter generation path.
- Existing slash command and dialog route projections still point chapter generation to `generate_chapter` for compatibility.
- The next migration should be deliberate: first expose the preferred route, then migrate planner/runtime behavior in a later phase.

## Scope

1. Add a read-only route preference service.
2. Register `inspect_agent_route_preference_projection` as an internal Agent preflight tool.
3. Project, for each dialog/slash route:
   - current tool,
   - current execution backend,
   - preferred tool chain,
   - whether an approval gate is required,
   - whether runtime routing has changed,
   - missing preferred tools,
   - migration status and reason.
4. Add tests that prove:
   - chapter routes prefer the approved prepare/execute chain,
   - non-chapter routes remain unchanged,
   - existing dialog/slash route projections are not mutated,
   - missing preferred tools degrade the projection instead of silently claiming readiness.

## Out Of Scope

- Changing `dialog_action_to_agent_tool_name`.
- Changing slash command execution behavior.
- Changing `plan_dialog_intent_agent_run` output.
- Changing chapter API behavior.
- Generating new novel chapters.

## Verification Plan

- T0 RED:
  - New route preference tests fail because the service/tool does not exist.
- T0 GREEN:
  - New route preference tests pass.
- T1 regression:
  - route preference tests,
  - existing slash/dialog route projection tests,
  - tool registry tests,
  - tool executor tests.
- Hygiene:
  - `git diff --check`,
  - secret scan over `backend` and active `docs`.

## Success Criteria

- `preview_chapter` routes still report current tool `generate_chapter`.
- `preview_chapter` routes also report preferred chain `prepare_generate_chapter_execution`, `execute_generate_chapter_with_approval`.
- Output explicitly says runtime route is unchanged.
- Existing route projection tests still pass without changing expected `generate_chapter` behavior.
