# Phase64 Report: Longform Batch Post Review Routing

## Summary

Phase64 added `route_longform_chapter_batch_after_review`, an internal Writing Agent tool that turns Phase63 post-generation review evidence into an explicit next route.

The tool consumes persisted Phase62 execution evidence and Phase63 review evidence from a selected background task. If the generated chapter needs revision, it records a recovery route backed by `plan_chapter_revision`. If the review passes, it prepares a next-batch preview through `build_longform_chapter_batch_plan`. It does not revise prose, enqueue work, run a task runner, or generate another chapter.

This phase completes the first auditable one-chapter loop: plan batch -> prepare execution -> execute one chapter -> review generated chapter -> route to revision or next batch preview.

## Reference Assimilation

Adopted:

- `openclaw` state-gated routing: every route validates current task state, execution hash, review hash, generated chapter existence, and batch bindings before any side effect.
- `hermes-agent` explicit decision contracts: route outputs include decision, rejected tools, selected tools, side effects, and bounded checkpoints.
- `openhuman` provenance discipline: routing stores hashes of upstream execution and review payloads so later Agent decisions can prove what evidence they consumed.

Not adopted:

- generic external agent runtime;
- unattended recursive generation loop;
- automatic revision draft creation;
- automatic next-batch enqueue;
- generic memory backend changes.

## Changes

- Added `backend/app/services/writing_agent/batch_post_review_router.py`.
- Registered `route_longform_chapter_batch_after_review` as an internal task-queue write tool.
- Added executor adapter and parameter normalization.
- Extended `inspect_longform_chapter_batch` selected task details with:
  - `post_generation_route_result`;
  - execution readiness statuses `phase64_routed_passed` and `phase64_routed_needs_revision`.
- Adjusted `chapter_revision_planner` to access `chapter_quality_review` through the module at runtime, preventing monkeypatched review functions from being captured as stale direct imports.
- Added tests for:
  - registry contract;
  - executor metadata and dispatch;
  - passed-review route to next batch preview;
  - blocked-review route to revision plan;
  - missing Phase63 review blocker;
  - review hash mismatch blocker;
  - idempotent repeat routing without duplicate side effects.

## Tool Contract

Input:

- `task_id`;
- optional `expected_post_generation_review_hash`;
- optional `next_batch_size`, minimum 1.

Success output:

- `status: "completed"`;
- `chapter_index`;
- `route_decision`;
- `post_generation_route_result`;
- `execution_checkpoint`;
- either `recovery_plan` or `next_batch_plan`;
- `recommended_next_tools`;
- `side_effects`;
- `trace`.

Blocked output:

- `status: "blocked"`;
- `reason`;
- no revision planning or next-batch planning if evidence validation fails.

Idempotent repeat output:

- `status: "skipped"`;
- `reason: "post_generation_route_already_recorded"`;
- existing `post_generation_route_result`.

## Side Effect Boundary

Allowed:

- call `plan_chapter_revision` only for `needs_revision` review results;
- call `build_longform_chapter_batch_plan` only for passed review results;
- write `post_generation_route_result`;
- append a `post_generation_route` execution checkpoint.

Explicitly skipped:

- `LocalTaskRunner`;
- `create_revision_draft`;
- `apply_planner_revision_patch`;
- next-batch enqueue;
- direct chapter generation;
- world-model proposal apply.

## Verification

RED focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "route_longform_chapter_batch_after_review or post_review_routing"
```

Result before implementation: `5 failed, 191 deselected`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "route_longform_chapter_batch_after_review or post_review_routing"
```

Result: `5 passed, 191 deselected in 0.46s`.

Branch check:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "routes_passed_longform_batch_review or routes_blocked_longform_batch_review"
```

Result: `2 passed, 151 deselected in 0.41s`.

Batch chain regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch or post_review_routing or route_longform_chapter_batch_after_review"
```

Result: `46 passed, 150 deselected in 2.62s`.

Hash mismatch check:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "post_review_routing_blocks_review_hash_mismatch"
```

Result: `1 passed, 153 deselected in 0.83s`.

Root-cause regression after T1 exposed stale monkeypatch capture:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "routes_blocked_longform_batch_review_to_revision_plan or plan_chapter_revision_maps_drift_findings_to_actions"
```

Result: `2 passed, 152 deselected in 0.33s`.

T1 related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `236 passed in 15.26s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed; it reported only the existing line-ending normalization warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. This was an orchestration stability phase: the goal was to make the Agent's single-chapter execution loop auditable before spending model calls on longer autonomous generation.

## Discovered Issues

- Phase63 review results existed, but the Agent had no durable routing decision after review.
- The passed-review and needs-revision paths were implicit and could be confused by later orchestration.
- There was no review-hash guard proving that a routing decision consumed the intended Phase63 result.
- A test revealed that `chapter_revision_planner` could capture a monkeypatched `review_chapter_quality` direct import if the module was first imported during a patched review route.

## Fixed Issues

- Added a post-review routing tool with strict Phase62/63 evidence validation.
- Added explicit revision and next-batch route outputs.
- Added review-hash and batch-execution-hash provenance.
- Added persisted routing evidence and inspector visibility.
- Fixed stale direct function import capture in `chapter_revision_planner`.
- Added idempotent repeat behavior for unchanged review evidence.

## Next Phase Boundary

The next phase should start the broader Agent Service control-plane migration. The existing `/` command module is only one compatibility entrypoint in that migration, not the target architecture.

Target direction:

- make conversation-driven Agent runs the primary orchestration surface;
- treat Hermes, Athena/world model, retrieval, knowledge base, review, task queue, Trace, and slash-command shortcuts as Agent-callable tools or tool entrypoints;
- avoid leaving major modules as parallel legacy control planes that bypass Agent runs, permissions, or Trace;
- adapt slash commands into intent shortcuts that resolve into Agent tool calls instead of keeping them as a separate command system;
- document command-to-tool routing, module-tool boundaries, permission boundaries, and regression tests before implementation.
