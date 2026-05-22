# Phase114 Direct Generate Approval Path Plan

## Objective

Add an Agent-native approved path for direct chapter generation without breaking the existing `generate_chapter` API/tool behavior used by the chapter endpoint.

## Assumptions

- `generate_chapter` is currently used by API control-plane chapter generation, so directly making it return `approval_required` would break existing frontend/API flows.
- The safer incremental step is to add a new prepare/execute pair with Agent plan approval verification, then migrate planner/dialog routes in later phases.
- The new execute path should call the same chapter generation implementation after approval is verified.

## Scope

1. Add `prepare_generate_chapter_execution`:
   - builds the canonical direct chapter generation Agent plan,
   - returns the Agent approval contract and hash,
   - performs no chapter write.
2. Add `execute_generate_chapter_with_approval`:
   - requires confirmation and approval contract hash,
   - verifies the canonical plan approval contract against live tool metadata,
   - calls `execute_generate_chapter_tool` only after verification passes.
3. Register both tools in the Agent tool registry and executor.
4. Update write gate coverage so the new execute tool is marked as Agent-plan-gate enforced and `generate_chapter` shows indirect approved coverage.

## Out Of Scope

- Changing the existing `generate_chapter` adapter behavior.
- Changing chapter API endpoint behavior.
- Migrating dialog/planner routes to the new prepare/execute pair.
- Running full frontend verification.

## Verification Plan

- T0 RED:
  - New direct generation execution tests fail because the service/tools do not exist.
- T0 GREEN:
  - New service tests pass.
- T1 regression:
  - direct generation execution tests,
  - write gate coverage tests,
  - approval metadata/contract tests,
  - tool registry tests,
  - tool executor tests.
- Hygiene:
  - `git diff --check`,
  - secret scan over `backend` and active `docs`.

## Success Criteria

- Prepare returns `approval_required` and does not write a chapter.
- Execute without valid approval is blocked before generation.
- Execute with a matching approval contract calls the chapter generation implementation.
- Existing `generate_chapter` adapter and API entrypoints are not changed in this phase.
