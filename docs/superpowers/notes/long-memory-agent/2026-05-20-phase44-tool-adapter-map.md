# Phase44 Report: Tool Adapter Map

## Phase Goal

Move the Writing Agent executor from a small branch dispatcher toward an explicit adapter map, then migrate low-risk read/report tools out of `run_service.py`.

## Implemented

- Added `_STATIC_TOOL_ADAPTERS` in `tool_executor.py`.
- Added `static_writing_agent_tool_adapter_names()` for diagnostics and tests.
- Migrated these tools into executor adapters:
  - `review_chapter_quality`;
  - `review_chapter_continuity`;
  - `plan_chapter_revision`;
  - `review_world_model_proposals`;
  - `plan_world_model_proposal_resolution`;
  - `preview_world_model_proposal_resolution`;
  - `draft_world_model_proposal_resolution_decisions`.
- Kept mutation-heavy tools in `run_service.py`:
  - `generate_chapter`;
  - `create_revision_draft`;
  - `apply_planner_revision_patch`;
  - `expand_chapter_to_target`;
  - `compress_chapter_to_target`;
  - `apply_world_model_proposal_resolution`;
  - `seed_continuity_anchor_proposals`.
- Added executor tests for:
  - adapter registry shape;
  - chapter report parameter normalization;
  - world proposal report parameter normalization;
  - legacy generation fallback.

## Debugging Note

The first T1 run exposed test contamination, not a production behavior regression.

Root cause: the new executor unit test monkeypatched `chapter_quality_review.review_chapter_quality` and then imported `chapter_revision_planner` while the dependency was patched. Because `chapter_revision_planner.py` imports `review_chapter_quality` at module load time, the fake function stayed captured in its module alias after monkeypatch teardown.

Fix: pre-import dependent modules before applying monkeypatches and patch the intended module object directly. After that, the previously failing API tests passed.

## Why This Helps Agentization

The Agent tool layer now has a scalable execution structure:

- run lifecycle remains centralized;
- tool adapters are explicit and testable;
- report tools can be moved without touching blocking semantics;
- future Athena, retrieval, knowledge base, and task queue tools can be added one adapter at a time.

This keeps module toolization incremental instead of turning `run_service.py` into another large execution registry.

## Validation

Validation level: T1.

Focused RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q
```

RED result:

```text
ImportError: cannot import name 'static_writing_agent_tool_adapter_names'
```

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py -q
```

Result:

```text
7 passed
```

Regression spot checks after fixing test isolation:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_plan_chapter_revision_maps_review_findings_to_actions tests\test_writing_agent_runs.py::test_agent_plan_world_model_proposal_resolution_orders_review_steps_without_writes tests\test_writing_agent_runs.py::test_agent_create_revision_draft_from_plan_is_non_destructive -q
```

Result:

```text
3 passed
```

T1 module verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result:

```text
129 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: exit 0
secret scan: exit 1; no matches
```

## Current Limits

- The executor still handles only synchronous adapters.
- `preflight_writing` still uses an injected callback because its implementation remains in `run_service.py`.
- Mutation-heavy tools remain in `run_service.py` pending targeted tests.
- The adapter map is explicit, not generated from descriptors.

## Next Phase Recommendation

Phase45 should introduce adapter metadata and execution metrics:

- adapter category and mutability flags;
- elapsed time and approximate output size in `agent_tool_result`;
- a clear list of unhandled internal tools for migration tracking;
- targeted migration of one mutation-light maintenance tool, likely `backfill_outline_gaps`, after tests pin behavior.
