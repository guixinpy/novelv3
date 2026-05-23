# Phase190 Route Preference Wrapper Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 route preference projection 对 setup / storyline / outline / chapter 生成入口都推荐 Agent approval wrapper，但不改变真实 slash/dialog runtime 路由。

**Architecture:** 保留 `inspect_agent_slash_command_route` 与 `inspect_agent_dialog_route_projection` 的当前执行后端判断；只增强 `inspect_agent_route_preference_projection` 的只读推荐层。新逻辑按当前 legacy tool 与 action_type 推导 preferred prepare/execute 链路，并继续输出 `runtime_behavior_changed == False`。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/tests/test_writing_agent_route_preference.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase190-route-preference-wrapper-projection.md`

## Success Criteria

- `preview_setup` / `preview_storyline` / `preview_outline` / `preview_chapter` routes all recommend their Agent approval chains.
- Runtime route fields remain unchanged:
  - `runtime_tool_name == current_tool_name`
  - `runtime_route_changed is False`
  - `runtime_behavior_changed is False`
- Projection status is `ready` when all preferred wrapper tools are statically supported.
- Projection degrades with clear `missing_preferred_tools` when a preferred wrapper is missing.

## Non-Scope

- Do not change real slash command execution.
- Do not change dialog control plane dispatch.
- Do not remove legacy action fallback.

## Tasks

### Task 1: RED Route Preference Tests

- [x] Update `_static_adapter_tools()` in `backend/tests/test_writing_agent_route_preference.py` to include setup/storyline/outline wrappers.
- [x] Replace the non-chapter no-change test with assertions that setup/storyline/outline recommend wrapper chains:

```python
def test_route_preference_recommends_approved_chains_for_hermes_routes_without_mutating_runtime_route():
    output = inspect_agent_route_preference_projection(
        static_adapter_tool_names=_static_adapter_tools(),
        action_execution_tool_names=_action_execution_tools(),
    )
    expected = {
        "preview_setup": [
            "prepare_generate_setup_execution",
            "execute_generate_setup_with_approval",
        ],
        "preview_storyline": [
            "prepare_generate_storyline_execution",
            "execute_generate_storyline_with_approval",
        ],
        "preview_outline": [
            "prepare_generate_outline_execution",
            "execute_generate_outline_with_approval",
        ],
    }

    assert output["status"] == "ready"
    for action_type, preferred_chain in expected.items():
        route = next(route for route in output["routes"] if route["source"] == "slash_command" and route["action_type"] == action_type)
        assert route["preferred_tool_chain"] == preferred_chain
        assert route["approval_gate_required"] is True
        assert route["runtime_tool_name"] == route["current_tool_name"]
        assert route["runtime_route_changed"] is False
        assert route["runtime_behavior_changed"] is False
        assert route["migration_status"] == "recommended_not_applied"
        assert route["missing_preferred_tools"] == []
```

- [x] Update degradation test so only chapter wrapper tools are missing.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
```

### Task 2: RED Executor Projection Test

- [x] Extend `test_tool_executor_handles_inspect_agent_route_preference_projection` to assert setup/storyline/outline recommended chains and unchanged runtime route.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
```

### Task 3: Implement Generic Preferred Chains

- [x] Replace chapter-only constants in `slash_command_route.py` with a mapping:

```python
APPROVED_GENERATION_CHAINS = {
    ("generate_setup", "preview_setup"): ("prepare_generate_setup_execution", "execute_generate_setup_with_approval"),
    ("generate_storyline", "preview_storyline"): ("prepare_generate_storyline_execution", "execute_generate_storyline_with_approval"),
    ("generate_outline", "preview_outline"): ("prepare_generate_outline_execution", "execute_generate_outline_with_approval"),
    ("generate_chapter", "preview_chapter"): ("prepare_generate_chapter_execution", "execute_generate_chapter_with_approval"),
    ("generate_chapter", "generate_chapter"): ("prepare_generate_chapter_execution", "execute_generate_chapter_with_approval"),
}
```

- [x] `_preferred_tool_chain` should return the mapped chain or `[current_tool_name]`.
- [x] Reason code should include the current tool name, for example `generate_setup_should_use_approved_agent_gate`.
- [x] Required approval fields remain `confirm_execute`, `approval_contract_hash`, `approval_contract`.

### Task 4: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_route_preference.py -q
python -m compileall backend/app/services/writing_agent
```

### Task 5: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase190-route-preference-wrapper-projection.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/tests/test_writing_agent_route_preference.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase190-route-preference-wrapper-projection.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase190-route-preference-wrapper-projection.md
git commit -m "feat: recommend hermes approval routes"
git push origin main
```
