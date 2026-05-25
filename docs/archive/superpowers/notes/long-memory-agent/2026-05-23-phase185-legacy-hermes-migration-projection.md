# Phase185 Legacy Hermes Migration Projection Report

## Goal

增加只读迁移投影工具，明确 `generate_setup`、`generate_storyline`、`generate_outline` 从 legacy Hermes action fallback 迁移为 Agent-native 工具所需的 preview / approval / execute 形态。

## Scope

本阶段新增一个只读 preflight 工具：

- `inspect_legacy_hermes_action_migration`

它只输出迁移路线，不新增 legacy Hermes static adapter，不改变实际执行调度。

## Changes

- 新增 `backend/app/services/writing_agent/legacy_hermes_migration_projection.py`
  - 输出三个 legacy Hermes action 的迁移项。
  - 每项包含当前执行路径、当前 mutability、推荐 Agent-native 工具形态、门禁字段、证据字段和风险说明。
- 更新 `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
  - 新增 `inspect_legacy_hermes_action_migration` descriptor。
  - target type 为 `agent_tool_migration_projection`。
- 更新 `backend/app/services/writing_agent/agent_core_tool_adapters.py`
  - 新增 static/read adapter。
- 更新测试：
  - core descriptor boundary list。
  - core adapter boundary list。
  - registry descriptor contract。
  - adapter metadata。
  - dispatch 输出内容。

## TDD Evidence

RED：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_legacy_hermes_migration_projection -q
```

结果：失败 2 项，descriptor 不存在。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration or agent_core_tool_adapters_live" -q
```

结果：失败 3 项，adapter metadata 和 dispatch 均不存在。

GREEN：

```powershell
pytest backend/tests/test_writing_agent_tool_registry.py::test_agent_core_tool_descriptors_live_in_dedicated_module backend/tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_legacy_hermes_migration_projection -q
```

结果：`2 passed in 0.03s`。

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "legacy_hermes_migration or agent_core_tool_adapters_live" -q
```

结果：`3 passed, 95 deselected in 0.13s`。

## Verification

T1 aggregation:

```powershell
pytest backend/tests/test_writing_agent_tool_aggregation_boundaries.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py -q
```

结果：`148 passed in 4.77s`。

Compile:

```powershell
python -m compileall backend/app/services/writing_agent
```

结果：exit 0。

Hygiene:

```powershell
git diff --check
```

结果：exit 0，无输出。

```powershell
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

结果：exit 1，无输出，未发现提交范围内的 DeepSeek/OpenAI 风格密钥。

## Next Phase Suggestion

下一阶段可以从 projection 进入第一条实际迁移链，优先选择 `generate_setup`：

- 先实现 `preview_generate_setup_execution` 和 `prepare_generate_setup_execution`。
- 再实现受 `confirm_execute` + `setup_plan_hash` 保护的 `execute_generate_setup_with_approval`。
- 保持 legacy fallback 兼容，直到前端/斜杠命令确认可以切换。
