# Phase60 Plan: Longform Batch Preflight Checkpoint

## Goal

Add the first controlled execution handoff for materialized `longform_chapter_batch` tasks.

This phase must not generate prose, start a runner, mutate the world model, or mark chapters complete. It only verifies a persisted batch task, builds a canonical execution handoff, runs safe preflight checks, writes a bounded checkpoint to the task result, and stops before `chapter_generation`.

## Assumptions

- Phase57 already provides a bounded batch DAG.
- Phase58 already materializes durable `longform_chapter_batch` tasks.
- Phase59 already exposes queue inspection.
- A real batch runner will be added later. Phase60 is the preflight checkpoint layer before that runner exists.

## Reference Assimilation

- `openclaw`: absorb canonical plan binding and explicit approval/evidence structure. Do not absorb host exec or sandbox systems.
- `hermes-agent`: absorb incremental checkpoint/resume discipline. Do not rely on prompt-text resume matching.
- `openhuman`: absorb `Proposal -> Preflight -> Approval -> Execute -> Verify -> Evidence` shape. Phase60 stops at preflight handoff.

## Implementation Scope

1. Add internal Writing Agent tool `execute_longform_chapter_batch_preflight`.
2. Validate the selected task is project-scoped and `task_type == "longform_chapter_batch"`.
3. Bind output to persisted `plan_hash`, chapter range, DAG node ids, and selected chapter indexes.
4. Run only the existing preflight gate for a bounded number of chapters.
5. Write `preflight_checkpoint` and bounded `execution_checkpoints` into `BackgroundTask.result`.
6. Keep task status unchanged. The task remains materialized-only until a real executor exists.
7. Return explicit skipped high-risk actions: `start_runner`, `generate_chapter`, `world_model_apply`.

## Out Of Scope

- Real chapter generation.
- LocalTaskRunner integration.
- Queue claiming, heartbeat, retry worker, or attempt table.
- World model intake/apply.
- Frontend queue visualization.
- Broad refactors of existing task service semantics.

## Test Plan

T0 focused tests:

- Registry exposes the new internal tool with target type `background_task`.
- Executor exposes and dispatches the new adapter.
- API run can preflight a materialized one-chapter batch and persist a checkpoint.
- API run blocks cleanly when selected chapter dependencies are not ready.
- Checkpoint confirms `can_execute_after_confirmation == false` for this phase and high-risk side effects are skipped.

T1 related regression:

- Existing Writing Agent batch plan/enqueue/inspect tests.
- Background task tests.

T2/T3 are not required unless the implementation touches shared task runner behavior.

## Success Criteria

- The Agent can inspect and preflight a queued longform batch through tools only.
- The checkpoint is durable and visible through the task result.
- No chapter content is created by the preflight tool.
- No world model or longform memory write is triggered.
- Focused T0 and related T1 tests pass.
