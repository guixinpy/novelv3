# Phase106 Dialog Intent Agent Plan Report

## Phase Summary

Phase106 connected Phase105 intent projection to a read-only Writing Agent run plan. The new bridge lets low-detail dialog input produce an auditable tool-chain plan without executing any tools.

## Goal Alignment

- Served the goal's Agent-first direction by turning natural-language dialog intent into an Agent planning input.
- Avoided solving longform stability by asking the user to write longer prompts.
- Kept the change narrow: no UI replacement, no automatic generation, no new runtime DAG.
- Continued reference-project learning through a read-only subagent architecture review of `openclaw`, `hermes-agent`, and `openhuman`.

## Implemented

- Added `backend/app/services/writing_agent/dialog_intent_planner.py`.
- Registered `plan_dialog_intent_agent_run` as an internal, read-only, non-blocking preflight tool.
- Added a static executor adapter for the new tool.
- Added tests for:
  - setup intent -> `setup_project` plan
  - chapter intent -> `continue_next_chapter` plan
  - unmatched chat input -> `no_plan`
  - static adapter coverage and unhandled-internal migration tracking

## Design Notes

- `IntentRouter.project()` remains the source of truth for text intent matching.
- The bridge does not re-guess intent from the raw prompt after projection.
- Supported Phase106 mappings:
  - `preview_setup` -> `setup_project`
  - `preview_chapter` -> `continue_next_chapter`
- Unsupported matched dialog actions return a blocked read-only report instead of guessing.
- Returned report includes `intent_projection`, `planner`, `plan`, `tools`, and `trace`.
- Trace links include `projection_id` and deterministic `plan_id`.

## Subagent Review

Read-only architecture review recommended keeping Phase106 narrow:

- Preserve source intent projection in the plan.
- Avoid full DAG/runtime/approval system in this phase.
- Prefer an auditable trace chain over a large logging refactor.
- Leave dynamic multi-tool competition and runtime approval events for later phases.

These recommendations were adopted for this phase.

## Novel Progress

No new novel chapter was generated in this phase. This phase improved the Agent entrypoint that will later let low-detail chapter requests produce a self-organized tool chain.

## Verification

T1 focused verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_intent_agent_plan" -q
```

Result:

```text
3 passed, 69 deselected
```

T1 planner/executor coverage:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_planner.py -k "dialog_intent_agent_plan or plan_dialog_intent_agent_run or planner or intent_projection or static_adapter_names or unhandled_internal" -q
```

Result:

```text
14 passed, 62 deselected
```

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

```text
No whitespace errors. No active secret matches.
```

## Next Phase Recommendation

Phase107 should add stable step metadata for plans: `step_id`, `source_projection_id`, `mutability`, and conservative `requires_confirmation` flags. This should remain read-only unless paired with an explicit execution confirmation contract.
