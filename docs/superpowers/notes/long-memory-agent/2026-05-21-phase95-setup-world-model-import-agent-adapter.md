# Phase95 Setup World Model Import Agent Adapter Report

## Goal

将 `import_setup_world_model` 从 `WritingAgentRunService` legacy special-case 分支迁移为 Agent-native static adapter，使世界模型初始化导入成为 Writing Agent 可统一编排、可投影、可审计的工具能力。

## Changes

- 新增 `backend/app/services/writing_agent/setup_world_model_import_tool.py`
  - 包装 `app.core.athena_longform.import_setup_to_world_model()`
  - 追加 Agent 输出字段：`should_generate_next_chapter`、`recommended_next_tools`
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_import_setup_world_model()` handler
  - 注册 `import_setup_world_model` static adapter
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_SETUP_WORLD_MODEL_IMPORT_OUTPUT`
  - 将 `import_setup_world_model.output_schema` 从 `_STATUS_OUTPUT` 改为结构化契约
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `import_setup_world_model` legacy branch
  - 当前未迁移的 legacy branch 仅剩 `seed_continuity_anchor_proposals`
- 更新测试
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_tool_registry.py`

## RED Evidence

命令：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "import_setup_world_model or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

结果：`6 failed, 2 passed, 79 deselected`

预期失败点：

- static adapter names 缺少 `import_setup_world_model`
- unhandled migration tracking 仍包含 `import_setup_world_model`
- adapter metadata 返回 `None`
- contract snapshot 中 adapter_type 仍为 `None`
- dispatch test 找不到 `setup_world_model_import_tool`
- registry output schema 仍只有 `status`

## GREEN Evidence

命令：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "import_setup_world_model or inspect_agent_tool_contracts or unhandled_internal_tools or static_adapter_names" -q
```

结果：`8 passed, 79 deselected`

## Regression Evidence

命令：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "import_setup_world_model" -q
```

结果：`1 passed, 161 deselected`

## Static Checks

- `git diff --check`：通过，无 whitespace error。
- `rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"`：无命中。
- `Select-String backend\app\services\writing_agent\run_service.py`：未发现 `import_setup_world_model` legacy branch 或 `import_setup_to_world_model` import 残留。

## Subagent Review

Reviewer: `019e4a0c-98e5-7913-8a7e-aede0b465c8c`

结论：

- 未发现 `run_service` legacy branch 残留。
- adapter metadata、category、mutability、handler name 与测试一致。
- output schema 已不再使用 `_STATUS_OUTPUT`。
- 测试覆盖 static adapter、migration tracking、contract snapshot、dispatch 和 registry schema。
- 无必须修复问题。

Reviewer 注意事项：

- `setup_world_model_import_tool.py` 和 Phase95 plan 是新增文件，提交前必须显式 `git add`。

## Next

下一阶段高价值候选：

- 迁移 `seed_continuity_anchor_proposals`，消除 `WritingAgentRunService` 中最后一个已知 internal legacy special-case。
- 继续从 `inspect_agent_tool_contracts` 输出中挑选 `missing_agent_native_adapter` 或 `output_schema_too_generic` 的高价值工具。
