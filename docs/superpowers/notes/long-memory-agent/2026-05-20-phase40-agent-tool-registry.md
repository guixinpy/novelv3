# Phase40 Report: Agent Tool Registry

## Phase Goal

Build the first compatibility layer for turning novelv3's existing modules into Agent-callable tools.

This phase followed the user's correction: the long goal is not centered on manually writing more chapters. The core work is upgrading novelv3 into a dedicated writing Agent by toolizing Hermes, Athena/world model, retrieval/review/maintenance capabilities so the Agent can discover, call, combine, and audit them.

## Reference Synthesis Used

- `openclaw`: tool descriptors, visible/hidden tool plan, availability diagnostics, guarded tool-result handling.
- `hermes-agent`: tool registry/toolset split, schema-driven tool descriptions, standard result/error shape, background review, session search.
- `openhuman`: complete-vs-visible capability split, data-defined subagents, memory tree, progress/events, explicit failure paths.

Applied conclusion: novelv3 needs its own domain-specific tool registry first. Do not copy external frameworks or add them as dependencies.

## Implemented

- Added `backend/app/services/writing_agent/tool_registry.py`.
- Introduced `AgentToolDescriptor` with:
  - `name`
  - `module`
  - `category`
  - `description`
  - `input_schema`
  - `output_schema`
  - `target_type`
  - `internal`
  - `non_blocking_report`
  - `availability_checks`
  - `warning_checks`
- Registered all existing Writing Agent tools plus the new read-only `describe_agent_tools`.
- Added `build_agent_tool_plan(...)` to return:
  - `visible_tools`
  - `hidden_tools`
  - `diagnostics`
  - `toolsets`
- Refactored `run_service.py` so allow-list, internal-tool list, report-tool list, and target-type lookup are derived from the registry.
- Added `describe_agent_tools` execution branch for Agent self-inspection.
- Added focused registry tests and API test.
- Corrected two stale length-policy test samples from `3000` to `3200`, because current elastic `2000-3000` policy treats `3000` as acceptable, not over-target.
- Updated the goal spec to capture the stronger Agent-engineering/toolization priority.

## Validation

Validation level: T1.

Reason:

- Backend compatibility slice.
- No database schema change.
- No frontend contract change beyond existing Agent run output shape.
- No large planner rewrite yet.

Commands run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q -k "tool_registry or describe_agent_tools or unsupported or run_and_step_persist"
```

Result:

```text
4 passed, 111 deselected
```

Then:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_keeps_historical_length_debt_out_of_recent_drift_warning -q
```

Result:

```text
1 passed
```

Then:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_runs.py -q
```

Result:

```text
115 passed
```

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

```text
git diff --check: passed
secret scan: no matches
```

## Findings

- `run_service.py` still contains the large `_execute_tool` dispatcher. This phase intentionally did not replace it.
- The new registry now gives the next phase a stable contract surface to build autonomous tool-chain planning.
- The registry currently models availability with lightweight DB checks. It does not yet enforce permissions or tool-result normalization beyond metadata.
- `describe_agent_tools` exposes capability state to Agent runs, but the Agent still does not autonomously plan from a high-level user goal.

## Novel Progress

No new chapter generated in this phase.

Reason: this phase was an Agent architecture/toolization slice. Continuing chapter generation without toolization would repeat the previous error: manual operation would mask missing Agent autonomy.

## Next Phase Recommendation

Phase41 should build the first autonomous tool-chain planner on top of this registry:

- Input: high-level user intent such as "继续生成下一章".
- Agent uses registry and project state to select a safe ordered chain:
  - `describe_agent_tools`
  - `preflight_writing`
  - missing dependency repair tools if needed
  - `generate_chapter`
  - quality/continuity review
  - world-model analysis/proposal tools
- The planner should produce an auditable plan before execution and record why each tool was chosen or skipped.

## Commit / Push

- Implementation commit: `a29eb90 feat: add writing agent tool registry`
- Remote: pushed to `origin/main`
