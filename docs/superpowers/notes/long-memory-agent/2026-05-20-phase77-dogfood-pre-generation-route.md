# Phase77 Report: Dogfood Pre-Generation Route

## Summary

Phase77 resumed the real `《雾港回声》` dogfood loop after the Agent infrastructure phases.

Input was intentionally low-detail:

```text
继续写下一章
```

The Writing Agent auto-plan generated Chapter 24 using the new pre-generation chain:

1. `describe_agent_tools`
2. `inspect_agent_knowledge_base_route`
3. `summarize_longform_context`
4. `preflight_writing`
5. `generate_chapter`
6. `review_chapter_quality`
7. `review_chapter_continuity`
8. `analyze_chapter_world_model`

## Baseline

Live dogfood project:

- project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- title: `雾港回声`
- target: `600` chapters / `1,200,000` words
- latest accepted chapter before this phase: Chapter 23 `暗渠追兵`
- Chapter 23 word count: `2926`
- outline count: `24`
- pending world proposals before generation: `0`
- background tasks: `0`

## Pre-Generation Route

Read-only route check for Chapter 24:

- Knowledge Base route: `sparse`
  - reason: `knowledge_base_sparse`
  - diagnostics: `world_truth_boundary`, `knowledge_base_sparse`
- Longform memory route: `ready`
  - reason: `longform_memory_ready`
  - retrieval documents: `82`
  - maintenance issue count: `0`
- World model route: `ready`
  - pending proposal count: `0`
- Agent job projection: empty queue
- Context summary: `ready`
  - sections: `global`, `volume`, `arc`, `recent_chapters`, `query_aware_retrieval`
- Preflight: `ready`
  - setup ready
  - outline chapter ready
  - historical outline gaps ready
  - world model profile ready
  - previous chapter ready
  - previous chapter state card ready
  - longform maintenance ready
  - length policy ready
  - retrieval ready

Conclusion: generation was allowed. The Knowledge Base being sparse is a non-blocking gap, but it is now visible to the Agent.

## Chapter 24 Result

Writing Agent run:

- run id: `2928c80b-206d-4740-afb7-73567f3202ab`
- status: `success`
- planner intent: `continue_next_chapter`

Generated chapter:

- chapter: `24`
- title: `雾中栖身`
- word count: `2436`
- status: `generated`

Forbidden/drift scan:

- `陆辞`: `0`
- `陆先生`: `0`
- `核心数据库`: `0`
- hard `N-07就是苏晚晴`: `0`
- `N-017`: `0`
- `完整公式`: `0`

Ending state:

- the group gets temporary shelter rather than resolving the pursuit arc;
- 雾安局 search pressure remains active;
- G-07 remains the next actionable direction;
- Su Wanqing remains weak/unresolved;
- no second-door shortcut or core-database shortcut appears.

## Post-Generation Review

Initial auto-run outputs:

- `review_chapter_quality`: `warning`
  - no intrinsic chapter quality issue codes;
  - recommended action: `review_world_model_proposals`
- `review_chapter_continuity`: `ready`
- `analyze_chapter_world_model`: created a Chapter 24 proposal bundle with `6` items.

World proposal queue after generation:

- total pending/actionable items: `6`
- high risk: `1`
- low risk: `5`
- predicates:
  - `event_summary`: `1`
  - `mentioned_in_chapter`: `1`
  - `presence_count`: `4`

The draft resolver produced decisions for all 6 items:

- `event_summary` -> `mark_uncertain`
- `mentioned_in_chapter` -> `reject`
- `presence_count` -> `reject`

Preview result:

- valid decisions: `6`
- invalid decisions: `0`
- remaining after preview: `0`
- would unblock generation: `true`

Guarded apply result:

- status: `ready`
- before actionable items: `6`
- after actionable items: `0`
- applied reviews: `6`
- invalid decisions: `0`

Final post-resolution checks:

- quality review: `ready`
- continuity review: `ready`
- world route for Chapter 25: `ready`
- memory route for Chapter 25: `ready`
- longform maintenance ready: `true`
- maintenance issue count: `0`
- retrieval: `86` documents / `166` chunks

## Findings

1. The expanded Agent pre-generation chain worked for a low-detail user intent.
2. The new Knowledge Base route is useful, but currently sparse for the dogfood project.
3. World-model proposal pressure remains the expected post-generation blocker and is correctly surfaced before the next chapter.
4. Existing guarded proposal-resolution tools were sufficient for this Chapter 24 proposal set.
5. The planner now reads creative memory before longform context, which is closer to the target Agent behavior.

## Issues Found

No new code blocker was found in this phase.

Product/system gap:

- Knowledge Base has read-side projection only. It can expose sparse state, but cannot yet persist candidate author preferences, project strategy lessons,拆书 patterns, or self-optimization learnings from dogfood runs.

## Verification

Runtime dogfood route:

```powershell
cd backend
.venv\Scripts\python.exe - <<'PY'
# Direct service execution against live dogfood DB:
# inspect_agent_knowledge_base_route
# inspect_agent_memory_route
# inspect_agent_world_model_route
# inspect_agent_job_projection
# summarize_longform_context
# WritingAgentRunService._preflight_writing
PY
```

Result:

- all readiness routes except sparse Knowledge Base were ready;
- preflight returned `ready`;
- no blocker issues.

Runtime generation:

```powershell
cd backend
.venv\Scripts\python.exe - <<'PY'
# WritingAgentRunService auto_plan:
# goal='继续写下一章'
# input={'auto_plan': True, 'chapter_index': 24}
PY
```

Result:

- run `2928c80b-206d-4740-afb7-73567f3202ab`
- status `success`
- generated Chapter 24 `雾中栖身`
- word count `2436`

Post-generation checks:

```powershell
cd backend
.venv\Scripts\python.exe - <<'PY'
# quality review, continuity review, world route, memory route,
# maintenance diagnostics, retrieval diagnostics, trace audit
PY
```

Result:

- final quality: `ready`
- final continuity: `ready`
- pending world proposals: `0`
- next world route: `ready`
- next memory route: `ready`
- maintenance issue count: `0`
- retrieval: `86` documents / `166` chunks

## Novel Progress

- latest generated chapter: `24`
- latest title: `雾中栖身`
- latest word count: `2436`
- next target: Chapter 25

## Next Phase Recommendation

Phase78 should add a write-side Knowledge Base candidate tool.

Minimum scope:

- create a read/write Agent tool that records candidate creative memory items from dogfood evidence;
- keep it separate from Athena world truth;
- support memory types like `author_preference`, `project_strategy`, `writing_pattern`, `self_optimization_lesson`;
- require source refs, confidence, and status;
- do not auto-inject all candidates into prompts until the read route can filter by status and relevance.

Reason: Phase77 proved the read route can reveal the sparse state, but the Agent still has no durable way to learn from this dogfood loop.
