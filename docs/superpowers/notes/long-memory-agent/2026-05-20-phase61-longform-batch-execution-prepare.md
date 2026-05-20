# Phase61 Report: Longform Batch Execution Prepare

## Summary

Phase61 added `prepare_longform_chapter_batch_execution`, an internal Writing Agent tool that turns a ready Phase60 preflight checkpoint into a stable attempt manifest and approval contract.

This phase still does not generate prose or start a runner. It creates the auditable execution intent that a future true executor must consume.

## Reference Assimilation

Adopted:

- `openclaw` exec approvals: bind future execution to a canonical context instead of approving a vague intent. For novelv3 this means binding `task_id`, `plan_hash`, chapter range, DAG node ids, selected chapters, and preflight checkpoint.
- `openclaw` Task Flow: keep durable multi-step flow state above individual tasks; Phase61 keeps the orchestration state inside the longform batch task result until a dedicated attempt table is justified.
- `hermes-agent` checkpoint manager: use stable hashes and bounded checkpoint history rather than trusting only mutable task status.
- `openhuman` approval model: represent approval as a contract plus audit-facing required confirmation, with fallback denial semantics.

Not adopted:

- host command approval and sandbox execution;
- generic autonomy modes;
- UI approval flows;
- external runner/heartbeat/attempt tables;
- automatic approval or LLM-based approval.

## Changes

- Added `backend/app/services/writing_agent/batch_execution_prepare.py`.
- Registered `prepare_longform_chapter_batch_execution` as an internal task-queue write tool.
- Added executor adapter metadata and dispatch.
- Extended `inspect_longform_chapter_batch` selected task details with:
  - `attempt_manifest`;
  - `approval_contract`.
- Added tests for:
  - registry contract;
  - executor metadata and dispatch;
  - ready preflight to approval-required manifest;
  - missing preflight blocker;
  - inspector visibility;
  - no chapter content side effect.

## Tool Contract

Input:

- `task_id` required.

Success output:

- `status: "approval_required"`;
- `attempt_manifest`;
- `attempt_manifest_hash`;
- `approval_contract`;
- `approval_contract_hash`;
- `required_confirmation` inside the approval contract;
- `recommended_next_tools: ["execute_longform_chapter_batch"]`.

The approval contract requires a future executor to provide:

- `confirm_execute: true`;
- `task_id`;
- `attempt_manifest_hash`;
- `approval_contract_hash`.

Blocked output:

- `status: "blocked"`;
- reason-specific `recommended_next_tools`;
- no manifest or approval contract persisted.

## Side Effect Boundary

Allowed:

- write `attempt_manifest`, `approval_contract`, and an `execution_prepare` checkpoint to `BackgroundTask.result`.

Forbidden:

- `LocalTaskRunner`;
- `generate_chapter`;
- `ChapterContent` creation/update;
- chapter-generation trace writes;
- world model intake/apply;
- longform memory writes;
- retrieval index writes;
- `WritingState` mutation;
- task status/progress mutation.

## Verification

RED focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "prepare_longform_chapter_batch_execution"
```

Result before implementation: `5 failed, 170 deselected`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "prepare_longform_chapter_batch_execution"
```

Result: `5 passed, 170 deselected in 0.39s`.

Batch chain regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `27 passed, 148 deselected in 1.31s`.

T1 related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `214 passed in 13.34s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed; it reported only the existing line-ending normalization warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Novel Progress

No new novel chapter was generated. This remains infrastructure work on the Agent task substrate before actual batch generation resumes.

## Discovered Issues

- Phase60 could prove a batch was safe up to preflight, but there was no stable approval artifact for future execution.
- A future executor would otherwise have to trust mutable task/result state without an auditable hash-bound handoff.

## Fixed Issues

- Added stable attempt manifest hashing.
- Added approval contract hashing and required confirmation payload.
- Added inspector visibility for execution preparation artifacts.
- Added blockers for missing or non-ready preflight checkpoints.

## Remaining Boundary

There is still no true `execute_longform_chapter_batch` runner. The next phase should consume the approval contract and implement the first narrowly-scoped execution step, likely generating one chapter from an approved one-chapter manifest while immediately checkpointing evidence.
