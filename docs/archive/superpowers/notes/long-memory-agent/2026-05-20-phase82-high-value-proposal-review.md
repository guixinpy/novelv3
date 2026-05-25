# Phase82 Report: High Value Proposal Review

## Summary

Phase82 added a conservative Agent path for handling the high-value world-model proposals introduced in Phase81.

The new tool drafts `mark_uncertain` decisions for high-value plot-signal predicates. It does not write reviews or facts by itself, and it must be followed by the existing guarded apply tool with explicit confirmation.

## Why This Matters

After Phase81, Chapter 25 correctly surfaced high-risk proposals:

- `access_permission_anomaly`
- `identifier_meaning_hypothesis`
- `investigation_lead`

The default batch resolver intentionally left them unclassified. That prevented unsafe auto-approval, but also left the Agent without a structured way to clear review pressure before continuing the novel.

Phase82 closes that gap without turning uncertain story clues into confirmed world truth.

## Changes

Created:

- `backend/app/core/high_value_world_proposal_resolution_draft.py`

Modified:

- `backend/app/services/writing_agent/tool_executor.py`
- `backend/app/services/writing_agent/tool_registry.py`
- `backend/app/services/writing_agent/run_service.py`
- `backend/tests/test_writing_agent_runs.py`

New Agent tool:

- `draft_high_value_world_proposal_resolution_decisions`

Tool behavior:

- reads actionable proposals in the current world profile;
- drafts decisions only for:
  - `identifier_meaning_hypothesis`
  - `access_permission_anomaly`
  - `investigation_lead`
- skips unrelated predicates;
- uses `mark_uncertain` for all supported high-value predicates;
- returns `recommended_next_tools: ["apply_world_model_proposal_resolution"]` when it drafts decisions;
- remains `report_only` and `can_auto_apply: false`.

Run-service follow-up rules now allow:

```text
draft_high_value_world_proposal_resolution_decisions
  -> apply_world_model_proposal_resolution
```

## Runtime Dogfood

Live dogfood project:

- project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- chapter: `25`

Before Phase82 runtime apply:

- actionable high-value proposals: `4`
- predicates:
  - `access_permission_anomaly`
  - `identifier_meaning_hypothesis`
  - `identifier_meaning_hypothesis`
  - `investigation_lead`

Draft result:

- status: `blocked`
- inspected: `4`
- draft decisions: `4`
- skipped: `0`
- actions: all `mark_uncertain`

Preview result:

- total actionable items: `4`
- valid decisions: `4`
- invalid decisions: `0`
- remaining after preview: `0`
- would unblock generation: `true`

Guarded apply result:

- status: `ready`
- before actionable items: `4`
- after actionable items: `0`
- applied reviews: `4`
- invalid decisions: `0`

Post-apply preflight for Chapter 26:

- status: `blocked`
- issue: `missing_outline_chapter`

This is expected and should be handled by the next dogfood generation auto-plan with `expand_outline_window`.

## Verification

Focused new-tool test:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_draft_high_value_world_proposal_resolution_decisions_reports_without_writes -q
```

Result:

- `1 passed`

Related proposal-resolution tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -k "draft_high_value_world_proposal_resolution_decisions or draft_world_model_proposal_resolution_decisions or apply_world_model_proposal_resolution" -q
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -k "world_model_proposal_resolution or tool_executor_exposes" -q
```

Result:

- `16 passed, 144 deselected`
- `17 passed, 24 deselected`

T2 related full files:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_tool_executor.py -q
```

Result:

- `201 passed in 15.00s`

## Remaining Issues

1. `mark_uncertain` clears pressure safely but does not materialize structured truth facts. This is acceptable for now but should be improved later.
2. The Agent still needs a richer high-value review mode that can distinguish:
   - clue to keep uncertain;
   - fact safe to approve with edits;
   - extraction false positive to reject.
3. Chapter 26 still lacks an outline and must be generated through the normal auto-plan path.

## Next Phase Recommendation

Phase83 should resume dogfood:

- input: `继续写下一章`
- target: Chapter 26
- expected auto-plan:
  - expand missing outline;
  - inspect Knowledge Base / memory / world route;
  - preflight;
  - generate Chapter 26;
  - review quality and continuity;
  - analyze world model;
  - handle proposal pressure with low-risk and high-value review tools as appropriate.
