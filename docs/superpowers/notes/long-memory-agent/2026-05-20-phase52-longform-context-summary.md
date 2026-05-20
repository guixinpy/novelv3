# Phase52 Report: Longform Context Summary Tool

## Summary

Phase52 adds `summarize_longform_context`, an internal read-only Writing Agent tool for inspecting longform project context before planning or generating chapters.

This moves the goal from recovery orchestration into core Agent autonomy: the Agent can now ask the system what longform context is currently available, where it came from, what is stale, and which sections are safe to use before it decides the next writing action.

## Reference Assimilation

The implementation adapts three reference patterns:

- `openclaw`: runtime-only context projection with auditable source sections.
- `hermes-agent`: bounded structured summaries instead of dumping raw context.
- `openhuman`: read-only planner posture and source-of-truth separation.

novelv3-specific translation:

- Athena/world model facts remain the truth layer.
- Longform memories and retrieval sections are context accelerators.
- The tool returns compact sections, `source_section_keys`, diagnostics, and trace metadata.
- Full `prompt_context` is opt-in through `include_prompt_context`.
- Stale memory/retrieval becomes diagnostics and recommended next work, not automatic repair.

## Changes

- Added `backend/app/services/writing_agent/longform_context_summary.py`.
- Registered `summarize_longform_context` in `backend/app/services/writing_agent/tool_registry.py`.
- Added a static read-only adapter in `backend/app/services/writing_agent/tool_executor.py`.
- Added registry tests for descriptor contract and target type.
- Added API test for Agent-run execution, bounded output, source keys, and adapter metadata.
- Added the Phase52 plan in `docs/superpowers/plans/long-memory-agent/2026-05-20-phase52-longform-context-summary.md`.

## Verification

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py -q -k "summarize_longform_context or contracts"
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "summarize_longform_context"
```

Result before implementation:

- registry: `2 failed, 3 deselected`, descriptor missing.
- API: `1 failed, 125 deselected`, run failed as unsupported tool.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py -q -k "summarize_longform_context or contracts"
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "summarize_longform_context"
```

Result:

- registry: `2 passed, 3 deselected`.
- API: `1 passed, 125 deselected`.

T1 Agent verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_registry.py -q
```

Result: `146 passed in 9.36s`.

Static checks:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

Result:

- `git diff --check` passed with only the existing CRLF warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Next Recommendation

Phase53 should make `plan_writing_agent_run` consume `summarize_longform_context` as a normal pre-generation step. That would let the Agent inspect current longform memory and diagnostics before deciding whether to generate, repair memory, expand outline, or review world-model proposals.
