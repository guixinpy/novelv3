# Phase113 Write Gate Coverage Plan

## Objective

Add a read-only Agent write gate coverage projection so the system can identify which write-capable tools are protected by Agent plan approval gates, which only have direct confirm/hash parameters, and which still need execution hardening.

## Assumptions

- Phase111 currently enforces Agent plan approval verification for `execute_longform_chapter_batch`.
- Some write-capable tools are still directly callable through static adapters without a persisted Agent plan approval contract.
- Before widening gates tool-by-tool, the Agent needs a compact coverage report to choose the next high-value target.

## Scope

1. Add a service that inspects registered Agent tool descriptors plus adapter metadata.
2. Project write-capable tools with:
   - mutability,
   - adapter presence,
   - direct confirm/hash fields,
   - Agent plan gate status,
   - indirect coverage notes,
   - risk level,
   - recommended next targets.
3. Register `inspect_agent_write_gate_coverage` as a read-only internal Agent tool.
4. Add focused tests for service output, registry contract, adapter metadata, and executor dispatch.

## Out Of Scope

- Adding new approval gates to specific write tools.
- Changing approval hash semantics.
- Changing `generate_chapter`, world model, revision, or task queue execution behavior.
- Running full frontend or full backend verification.

## Verification Plan

- T0 RED:
  - New service tests fail because `write_gate_coverage.py` does not exist.
- T0 GREEN:
  - New service tests pass.
- T1 regression:
  - service tests,
  - tool registry tests,
  - tool executor tests,
  - approval metadata/contract tests.
- Hygiene:
  - `git diff --check`,
  - secret scan over `backend` and active `docs`.

## Success Criteria

- `execute_longform_chapter_batch` is reported as Agent-plan-gate enforced.
- `generate_chapter` is reported as directly callable without direct confirmation and only indirectly covered by the batch path.
- Tools such as `apply_world_model_proposal_resolution` are reported as direct confirm/hash guarded but still missing Agent plan approval gate enforcement.
- Output includes a sorted list of next write gate targets for future phases.
