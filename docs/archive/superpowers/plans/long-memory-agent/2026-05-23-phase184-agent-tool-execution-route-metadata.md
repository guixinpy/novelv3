# Phase184 Agent Tool Execution Route Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在工具合同快照和 Agent run 结果 envelope 中显式暴露工具执行路径。

**Architecture:** 新增轻量 route 推断逻辑：有 adapter metadata 时按 `static_adapter` / `injected_adapter` 标记；无 adapter 但 public descriptor 存在时标记 `legacy_action_fallback`；无 descriptor 标记 `unsupported`；internal descriptor 无 adapter 标记 `unsupported_internal`。这样 Agent 和审计链可以明确区分 legacy fallback 与真正的 Agent-native 工具。

**Tech Stack:** Python 3、pytest、Writing Agent service layer。

---

## Files

- Modify: `backend/app/services/writing_agent/tool_contracts.py`
  - Add `execution_route` to every tool contract.
  - Add a small `_execution_route(...)` helper.
- Modify: `backend/app/services/writing_agent/run_service.py`
  - Add `execution_route` to `agent_tool_result` envelope.
  - Add a small `_execution_route_for_tool(...)` helper.
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - Assert contract snapshot distinguishes `legacy_action_fallback`, `static_adapter`, and `injected_adapter`.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert legacy action run envelope reports `legacy_action_fallback`.
  - Assert static adapter envelope reports `static_adapter`.
  - Assert unsupported tool envelope reports `unsupported`.

## Success Criteria

- `inspect_agent_tool_contracts` reports:
  - `generate_setup.execution_route == "legacy_action_fallback"`
  - `generate_chapter.execution_route == "static_adapter"`
  - `preflight_writing.execution_route == "injected_adapter"`
- Agent run result envelope reports:
  - legacy `generate_setup` route as `legacy_action_fallback`
  - existing adapter metadata remains unchanged.
- No legacy Hermes static adapter is added in this phase.

## Non-Scope

- Do not change actual execution dispatch.
- Do not change legacy Hermes action fallback behavior.
- Do not add approval gates to legacy actions yet.

## Tasks

### Task 1: RED Contract Snapshot Test

- [x] In `backend/tests/test_writing_agent_tool_executor.py`, extend `test_tool_executor_handles_inspect_agent_tool_contracts`:

```python
assert tools_by_name["generate_setup"]["execution_route"] == "legacy_action_fallback"
assert tools_by_name["generate_chapter"]["execution_route"] == "static_adapter"
assert tools_by_name["preflight_writing"]["execution_route"] == "injected_adapter"
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
```

Expected: FAIL with missing `execution_route`.

### Task 2: RED Run Envelope Test

- [x] In `backend/tests/test_writing_agent_runs.py`, extend `test_create_agent_run_records_steps_and_returns_detail`:

```python
envelope = payload["steps"][0]["output"]["agent_tool_result"]
assert envelope["execution_route"] == "legacy_action_fallback"
assert envelope["adapter"] is None
```

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_runs.py::test_create_agent_run_records_steps_and_returns_detail -q
```

Expected: FAIL with missing `execution_route`.

### Task 3: Implement Contract Execution Route

- [x] In `backend/app/services/writing_agent/tool_contracts.py`, add to contract dict:

```python
"execution_route": _execution_route(descriptor, adapter_metadata),
```

- [x] Add helper:

```python
def _execution_route(descriptor: AgentToolDescriptor, adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    if descriptor.internal:
        return "unsupported_internal"
    return "legacy_action_fallback"
```

### Task 4: Implement Run Envelope Execution Route

- [x] In `backend/app/services/writing_agent/run_service.py`, import `get_agent_tool_descriptor`.
- [x] In `_agent_tool_result_envelope(...)`, compute adapter once:

```python
adapter = writing_agent_tool_adapter_metadata(step.tool_name)
```

- [x] Add to envelope:

```python
"adapter": adapter,
"execution_route": _execution_route_for_tool(step.tool_name, adapter),
```

- [x] Add helper:

```python
def _execution_route_for_tool(tool_name: str, adapter_metadata: dict[str, Any] | None) -> str:
    if adapter_metadata:
        adapter_type = str(adapter_metadata.get("adapter_type") or "adapter")
        return f"{adapter_type}_adapter"
    descriptor = get_agent_tool_descriptor(tool_name)
    if descriptor is None:
        return "unsupported"
    if descriptor.internal:
        return "unsupported_internal"
    return "legacy_action_fallback"
```

### Task 5: Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_inspect_agent_tool_contracts -q
pytest backend/tests/test_writing_agent_runs.py::test_create_agent_run_records_steps_and_returns_detail -q
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -q
python -m compileall backend/app/services/writing_agent
```

### Task 6: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase184-agent-tool-execution-route-metadata.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/tool_contracts.py backend/app/services/writing_agent/run_service.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase184-agent-tool-execution-route-metadata.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase184-agent-tool-execution-route-metadata.md
git commit -m "feat: expose agent tool execution routes"
git push origin main
```
