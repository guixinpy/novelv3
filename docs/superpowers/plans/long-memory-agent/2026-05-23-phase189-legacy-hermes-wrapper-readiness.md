# Phase189 Legacy Hermes Wrapper Readiness Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 更新 legacy Hermes 迁移投影，使 `generate_setup`、`generate_storyline`、`generate_outline` 能识别 Phase186-188 已提供的 Agent approval wrapper。

**Architecture:** 保留 legacy public tool 的 `current_execution_route == legacy_action_fallback`，因为 slash/dialog 还没切到新链路；新增 wrapper readiness 字段，让 Agent 知道可用的 preview / prepare / execute wrapper 已就绪。投影不执行写入，只读 adapter metadata。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Modify: `backend/app/services/writing_agent/legacy_hermes_migration_projection.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase189-legacy-hermes-wrapper-readiness.md`

## Success Criteria

- `inspect_legacy_hermes_action_migration` still reports three legacy actions.
- Direct legacy actions still show `current_execution_route == legacy_action_fallback`.
- Each action reports:
  - `migration_stage == agent_native_wrapper_ready`
  - `agent_native_execution_route == static_adapter`
  - `approval_wrapper.execute_adapter_exists == True`
- Summary reports `agent_native_ready_count == 3`.

## Non-Scope

- Do not switch slash/dialog route execution.
- Do not add new generation tools.
- Do not remove legacy descriptors or action fallback.

## Tasks

### Task 1: RED Projection Test

- [x] Update `test_tool_executor_handles_legacy_hermes_migration_projection` to assert all three legacy actions are wrapper-ready:

```python
assert result.output["summary"]["agent_native_ready_count"] == 3
for tool_name, execute_tool in {
    "generate_setup": "execute_generate_setup_with_approval",
    "generate_storyline": "execute_generate_storyline_with_approval",
    "generate_outline": "execute_generate_outline_with_approval",
}.items():
    item = tools_by_name[tool_name]
    assert item["current_execution_route"] == "legacy_action_fallback"
    assert item["migration_stage"] == "agent_native_wrapper_ready"
    assert item["agent_native_execution_route"] == "static_adapter"
    assert item["approval_wrapper"]["execute_tool"] == execute_tool
    assert item["approval_wrapper"]["execute_adapter_exists"] is True
```

- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration_projection" -q
```

### Task 2: Implement Projection

- [x] In `legacy_hermes_migration_projection.py`, derive wrapper names from `recommended_agent_native_shape`.
- [x] Look up wrapper metadata from `adapter_metadata_by_name`.
- [x] Add `agent_native_execution_route`, `approval_wrapper`, and wrapper-aware `migration_stage`.
- [x] Count wrapper-ready tools in `agent_native_ready_count`.

### Task 3: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration_projection" -q
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
python -m compileall backend/app/services/writing_agent
```

### Task 4: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase189-legacy-hermes-wrapper-readiness.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/legacy_hermes_migration_projection.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase189-legacy-hermes-wrapper-readiness.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase189-legacy-hermes-wrapper-readiness.md
git commit -m "feat: report hermes wrapper readiness"
git push origin main
```
