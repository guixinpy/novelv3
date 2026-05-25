# Phase 17 Report: Agent Length Feedback and Chapter 6 Loop

## Summary

Phase17 added deterministic Writing Agent length feedback for `generate_chapter` tool calls, then used it to generate Chapter 6 of `《雾港回声》` without manual length instructions.

The main code change is in `WritingAgentRunService._execute_tool`: when the Agent invokes `generate_chapter`, the run service now checks existing longform length policy diagnostics, appends corrective feedback to `command_args` when repeated drift exists, and records `agent_generation_feedback` in the step output.

## Code Changes

- Added over-target feedback when recent generated chapters repeatedly exceed the active longform target.
- Added under-target feedback when recent generated chapters repeatedly fall below the active longform target.
- Preserved operator/user `command_args` and appended Agent feedback after it.
- Kept chapter prompt provider and database schema unchanged.
- Added regression coverage in `backend/tests/test_writing_agent_runs.py`.

## TDD Evidence

RED command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift -q
```

Initial result: failed before implementation because `command_args` did not include Agent feedback.

GREEN command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift tests\test_writing_agent_runs.py::test_agent_run_records_chapter_length_and_world_model_diagnostics tests\test_writing_agent_runs.py::test_agent_preflight_warns_when_repeated_over_target_drift_requires_review -q
```

Result: `4 passed in 0.40s`.

T2 verification command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `119 passed in 12.98s`.

## Dogfood: Chapter 6

Project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

Generated chapter:

- Chapter: 6
- Title: `黑市雾晶`
- Chapter id: `e46454fd-8d4b-4379-b4fc-25809ff7d011`
- Status: `generated`
- Stored word count: `2153`
- Content char count: `2675`
- Model: `deepseek-v4-flash`

Generation run:

- Run id: `c3820f08-b1bd-4085-9497-db56fdddfa53`
- Trace id: `46b0f60f-b2d9-4d4c-9c48-d259bcfc4b76`
- Status: `success`
- Preflight status: `ready`
- Preflight warning: existing repeated over-target drift required length attention.
- Generation feedback reason: `repeated_over_target`
- Feedback range: `2000-2300`
- Length decision: `within`

Review and world-model runs:

- Review/analyze run id: `de483430-04a4-4b50-98f0-166bb5ae69ce`
- Initial quality status: `warning`, because generated world-model proposals required review.
- Draft proposal review run id: `44ee3482-c50e-4f1a-81a2-cfba3497dd2a`
- Apply proposal review run id: `d994c0c0-5057-4cb3-ac6d-4d3cdf1751fb`
- Proposal result: pending `8 -> 0`, reviews `39 -> 47`, fact claims stayed `0`.
- Final quality run id: `472b116e-9251-4420-94d4-cd3a1d4dbbb8`
- Final status: `ready`
- Final blockers: `0`

Current database check:

- Generated chapters: `6`
- World proposal items: `47`
- World proposal reviews: `47`
- Pending world proposal items: `0`
- World fact claims: `0`

## Subagent Quality Review

The read-only reviewer found Chapter 6 usable as dogfood output but not as a quality benchmark.

Positive signals:

- Chapter 6 is actual prose, not outline text.
- It connects to Chapter 5 through the lower-city route, blank-letter clue, fog crystal clue, and black market objective.
- It has a readable web-novel rhythm: market entry, negotiation, enemy pressure, escape, clue confirmation, chapter hook.

Issues to feed into later phases:

- `叶知秋` drifted from the established female neuro-science professor profile into a male former bureau researcher.
- `苏晚晴` gained an active illusion-making capability, while the known setup only supports fog perception and side effects.
- Existing fog crystal versus purchased memory fog crystal was not clearly distinguished.
- `赵猛/老赵` identity weight weakened from gang leader/controller of the black market into a stallholder-like role.
- The key item acquisition was too convenient; the story needs stronger cost, debt, bargain, or risk checks.
- The outline itself appears to contain some ability drift, so consistency checks must run before generation, not only after.
- World fact claims remain `0`, which means later generation still lacks approved hard facts.
- Longform memory summaries need more plot-state information, not only range/count metadata.
- The current outline only covers 8 chapters, so a later phase must address rolling expansion toward 600+ chapters.

## Next Phase Recommendation

Phase18 should focus on continuity and quality gates rather than another pure generation step:

- Add a "previous chapter state card" before generation: location, held items, unresolved hooks, active emotions, and next action.
- Add character identity and gender/role drift detection against world model and setup data.
- Add ability-boundary checks for character powers and constraints.
- Add convenience-cost review for rare item acquisition and critical clue access.
- Start converting approved or low-risk story facts into durable world fact claims, or explicitly document why they remain proposal-only.

After those gates exist, generate Chapter 7 and verify whether the Agent can use the new state card and consistency checks without excessive full-stack validation.
